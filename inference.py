#!/usr/bin/env python3
"""
Gwen-TTS: Vietnamese Voice Cloning Inference

Usage:
    # Using a built-in reference speaker
    python inference.py --text "Xin chào Việt Nam" --speaker yen_nhi

    # Using a custom reference audio
    python inference.py --text "Xin chào" --ref_audio my_voice.wav --ref_text "transcript of audio"

    # Using HuggingFace model (auto-download)
    python inference.py --text "Xin chào" --speaker yen_nhi --model_path g-group-ai-lab/gwen-tts-0.6B

    # List available speakers
    python inference.py --list_speakers
"""

import argparse
import json
import os
import sys
from pathlib import Path

import torch
import numpy as np
import soundfile as sf

# Recommended generation config for Gwen-TTS
# These parameters are optimized for natural Vietnamese voice cloning
GENERATION_CONFIG = dict(
    temperature=0.7,
    top_k=50,
    top_p=0.9,
    max_new_tokens=4096,
    repetition_penalty=1.0,
    subtalker_dosample=True,
    subtalker_temperature=0.7,
    subtalker_top_k=50,
    subtalker_top_p=0.9,
)

# Theanh28 style: Lower temperatures force the model to closely replicate
# the reference speaker's characteristics (high pitch, dramatic tone).
# - subtalker_temperature=0.1: Forces near-deterministic speaker identity replication
# - temperature=0.3: Tighter prosody, less deviation from reference rhythm
# - repetition_penalty=1.2: Prevents monotone repetition on long text
THEANH28_GENERATION_CONFIG = dict(
    temperature=0.3,
    top_k=20,
    top_p=0.85,
    max_new_tokens=4096,
    repetition_penalty=1.2,
    subtalker_dosample=True,
    subtalker_temperature=0.1,
    subtalker_top_k=20,
    subtalker_top_p=0.85,
)

# Pitch shift for Theanh28 voice matching (in semitones).
# The model tends to output lower pitch than the reference speaker.
# This post-processing step compensates by shifting pitch UP.
# Note: +2.0 is a conservative default to avoid phase vocoder artifacts.
# User can fine-tune via the slider (0 to +6.0).
THEANH28_PITCH_SHIFT_SEMITONES = 2.0


def load_model(model_path, device="cuda:0", dtype=None):
    """Load the Gwen-TTS model."""
    from qwen_tts import Qwen3TTSModel

    # Mac (MPS or CPU) should use float32 or float16 to avoid bfloat16 corruption. 
    # bfloat16 is usually only safe on modern Nvidia GPUs.
    if dtype is None:
        if "cuda" in device:
            dtype = torch.bfloat16
        elif "mps" in device:
            dtype = torch.float32
        else:
            dtype = torch.float32

    try:
        import flash_attn  # noqa: F401
        attn_impl = "flash_attention_2" if "cuda" in device else "sdpa"
    except Exception:
        attn_impl = "sdpa"
        print("Note: flash-attn not available, using sdpa attention (slightly slower)")

    model = Qwen3TTSModel.from_pretrained(
        model_path,
        device_map=device,
        dtype=dtype,
        attn_implementation=attn_impl,
    )
    return model


def load_speaker_info(ref_info_path):
    """Load reference speaker metadata."""
    import json
    with open(ref_info_path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_vietnamese(text, theanh28_style=False):
    """Full Vietnamese text normalization for TTS.
    
    Converts numbers, symbols, abbreviations, dates, times, currencies,
    and special characters into spoken Vietnamese to prevent Chinese
    pronunciation from the Qwen3 base model.
    
    See text_normalizer.py for the full implementation.
    """
    from text_normalizer import normalize_vietnamese as _normalize
    return _normalize(text, theanh28_style=theanh28_style)


# Warmup duration estimate: how many seconds of audio the ". " prefix
# typically produces. We set this to 0.0 to avoid accidentally cutting off
# the actual first words of the text if the model generates the prefix quickly.
# A slight pause at the
WARMUP_TRIM_SECONDS = 0.0


def _trim_warmup_audio(wav, sr, trim_seconds=WARMUP_TRIM_SECONDS):
    """Trim warmup prefix audio from the start of generated speech.
    
    Args:
        wav: numpy array of audio samples
        sr: sample rate
        trim_seconds: seconds to trim from start
    
    Returns:
        Trimmed audio array
    """
    if trim_seconds <= 0:
        return wav
        
    trim_samples = int(trim_seconds * sr)
    if trim_samples >= len(wav):
        return wav  # Don't trim if audio is shorter than warmup
    return wav[trim_samples:]


def _pitch_shift_audio(wav, sr, semitones):
    """Shift pitch of audio by N semitones without changing speed.
    
    Uses librosa's pitch_shift with speech-optimized parameters:
    - n_fft=512 (default 2048): Smaller FFT window reduces reverb/echo
      artifacts that the phase vocoder creates on voice frequencies.
    - hop_length=128: Correspondingly smaller hop for smoother output.
    
    Args:
        wav: numpy array of audio samples
        sr: sample rate
        semitones: number of semitones to shift (positive = higher pitch)
    
    Returns:
        Pitch-shifted audio array
    """
    if semitones == 0:
        return wav
    
    import librosa
    print(f"[Pitch Shift] Nâng pitch +{semitones} semitones để khớp giọng tham chiếu...")
    
    # Speech-optimized parameters:
    # - n_fft=512: Small window avoids echo/vang on voice (default 2048 is for music)
    # - hop_length=128: Fine-grained time resolution for speech transients
    shifted = librosa.effects.pitch_shift(
        y=wav, sr=sr, n_steps=semitones,
        n_fft=512,
        hop_length=128,
    )
    return shifted




def generate_voice_clone(model, text, language, ref_audio, ref_text,
                         theanh28_style=False, use_tight_config=False,
                         pitch_shift=None):
    """Generate speech using voice cloning.
    
    Args:
        model: Loaded Gwen-TTS model
        text: Text to synthesize
        language: Language identifier
        ref_audio: Path to reference audio file
        ref_text: Transcript of reference audio
        theanh28_style: If True, apply text manipulation (. → !! , → ! etc.)
                       for dramatic reading. Only from checkbox, never auto.
        use_tight_config: If True, use low temperature config to stay
                         closer to the reference speaker's voice/style.
                         Auto-enabled for theanh speakers.
        pitch_shift: Semitones to shift pitch AFTER generation.
                    Only applied when explicitly set (e.g., from slider).
    """
    from text_normalizer import VIETNAMESE_WARMUP_PREFIX, VIETNAMESE_WARMUP_ENABLED
    
    text = normalize_vietnamese(text, theanh28_style=theanh28_style)
    ref_text = normalize_vietnamese(ref_text)
    
    # Add warmup prefix to prevent first-word clipping
    use_warmup = VIETNAMESE_WARMUP_ENABLED and language.lower() == "vietnamese"
    if use_warmup:
        text = VIETNAMESE_WARMUP_PREFIX + text
    
    # Select generation config:
    # - Tight config: low temperature → model stays close to reference voice
    # - Standard config: more creative freedom
    if use_tight_config or theanh28_style:
        gen_config = THEANH28_GENERATION_CONFIG
        print("[Config] Tham số chặt — bám sát giọng tham chiếu")
    else:
        gen_config = GENERATION_CONFIG
    
    if theanh28_style:
        print("[Style] Nhấn nhá cảm xúc (. → !! , → ! ! → !!!)")
    
    wavs, sr = model.generate_voice_clone(
        text=text,
        language=language,
        ref_audio=ref_audio,
        ref_text=ref_text,
        **gen_config,
    )
    
    result = wavs[0]
    
    # Trim warmup audio from the start
    if use_warmup:
        result = _trim_warmup_audio(result, sr)
    
    # Post-processing pitch shift — ONLY when explicitly requested.
    if pitch_shift and pitch_shift != 0:
        result = _pitch_shift_audio(result, sr, pitch_shift)
    
    return result, sr


def generate_with_speaker(model, text, language, speaker_key, ref_info, base_dir,
                          theanh28_style=False, use_tight_config=False,
                          pitch_shift=None):
    """Generate speech using a built-in reference speaker."""
    if speaker_key not in ref_info:
        available = ", ".join(ref_info.keys())
        raise ValueError(f"Speaker '{speaker_key}' not found. Available: {available}")

    speaker = ref_info[speaker_key]
    ref_audio_path = os.path.join(base_dir, speaker["audio_path"])
    ref_text = speaker["text"]

    return generate_voice_clone(
        model, text, language, ref_audio_path, ref_text,
        theanh28_style=theanh28_style,
        use_tight_config=use_tight_config,
        pitch_shift=pitch_shift,
    )


def main():
    parser = argparse.ArgumentParser(description="Gwen-TTS: Vietnamese Voice Cloning")
    parser.add_argument("--text", type=str, help="Text to synthesize")
    parser.add_argument(
        "--speaker", type=str, default=None,
        help="Built-in speaker key (e.g., yen_nhi, khanh_toan)",
    )
    parser.add_argument(
        "--ref_audio", type=str, default=None,
        help="Path to custom reference audio WAV file",
    )
    parser.add_argument(
        "--ref_text", type=str, default=None,
        help="Transcript of the reference audio",
    )
    parser.add_argument(
        "--language", type=str, default="vietnamese",
        help="Language (default: vietnamese)",
    )
    parser.add_argument(
        "--model_path", type=str, default="g-group-ai-lab/gwen-tts-0.6B",
        help="Path to model or HuggingFace model ID (default: g-group-ai-lab/gwen-tts-0.6B)",
    )
    parser.add_argument(
        "--output", type=str, default="output.wav",
        help="Output WAV file path (default: output.wav)",
    )
    parser.add_argument(
        "--device", type=str, default="cuda:0",
        help="Device (default: cuda:0)",
    )
    parser.add_argument(
        "--theanh28", action="store_true",
        help="Enable Theanh28 style: text manipulation (. → !!) + pitch shift",
    )
    parser.add_argument(
        "--pitch_shift", type=float, default=None,
        help="Pitch shift in semitones (e.g., 2.0 = higher). "
             "Only applied when --theanh28 checkbox is checked.",
    )
    parser.add_argument(
        "--list_speakers", action="store_true",
        help="List available built-in speakers and exit",
    )

    args = parser.parse_args()

    base_dir = Path(__file__).parent
    ref_info_path = base_dir / "data" / "ref_info.json"

    if args.list_speakers:
        if ref_info_path.exists():
            ref_info = load_speaker_info(ref_info_path)
            print("Available speakers:")
            for key, info in ref_info.items():
                print(f"  {key:20s} - {info['name']}")
        else:
            print("ref_info.json not found.")
        sys.exit(0)

    if not args.text:
        parser.error("--text is required")
    if args.speaker is None and args.ref_audio is None:
        parser.error("Either --speaker or --ref_audio must be provided")
    if args.ref_audio and not args.ref_text:
        parser.error("--ref_text is required when using --ref_audio")

    print(f"Loading model from {args.model_path}...")
    model = load_model(args.model_path, device=args.device)
    print("Model loaded successfully.")

    # ── Logic ────────────────────────────────────────────────────────
    #
    # Auto-detect theanh speaker → use_tight_config = True
    #   → Model uses low temperature to stay close to reference voice.
    #   → Text is NOT modified — model reads clean Vietnamese naturally.
    #
    # Checkbox --theanh28 → theanh28_style = True
    #   → Text manipulation (. → !! , → ! ! → !!! ? → ???)
    #   → Also enables tight config + optional pitch shift.
    #   → This is EXPERIMENTAL and may make output less natural.
    # ─────────────────────────────────────────────────────────────────
    
    # Auto-detect theanh speaker
    if args.speaker:
        is_theanh_speaker = "theanh" in args.speaker.lower()
    else:
        is_theanh_speaker = "theanh" in str(args.ref_audio).lower()
    
    # Tight config: auto for theanh speakers (stays close to reference)
    use_tight_config = is_theanh_speaker
    
    # Text manipulation: ONLY from checkbox (never auto)
    theanh28_style = args.theanh28
    
    if is_theanh_speaker and not args.theanh28:
        print("[Auto] Giọng Theanh → tight config (bám sát giọng gốc, không thay đổi text)")

    if args.speaker:
        ref_info = load_speaker_info(ref_info_path)
        print(f"Generating with speaker: {ref_info[args.speaker]['name']}...")
        wav, sr = generate_with_speaker(
            model, args.text, args.language, args.speaker, ref_info, base_dir,
            theanh28_style=theanh28_style,
            use_tight_config=use_tight_config,
            pitch_shift=args.pitch_shift,
        )
    else:
        print(f"Generating with custom reference audio: {args.ref_audio}...")
        wav, sr = generate_voice_clone(
            model, args.text, args.language, args.ref_audio, args.ref_text,
            theanh28_style=theanh28_style,
            use_tight_config=use_tight_config,
            pitch_shift=args.pitch_shift,
        )

    sf.write(args.output, wav, sr)
    print(f"Saved to {args.output} (sample rate: {sr}Hz)")


if __name__ == "__main__":
    main()
