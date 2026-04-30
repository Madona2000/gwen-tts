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
# These parameters are optimized for natural Vietnamese voice cloning.
# NOTE: For Custom Clone (ICL mode), the model must stay CLOSE to the reference
# speaker. Lower temperature = less drift toward the model's training dominant
# language (Chinese). temperature=0.7 is too high and causes Chinese bleed-through.
GENERATION_CONFIG = dict(
    temperature=0.3,
    top_k=30,
    top_p=0.85,
    max_new_tokens=4096,
    repetition_penalty=1.05,
    subtalker_dosample=True,
    subtalker_temperature=0.3,
    subtalker_top_k=30,
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
        import flash_attn  # type: ignore # noqa: F401
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


# Warmup trim disabled — prefix removed to avoid alien sounds at start.
WARMUP_TRIM_SECONDS = 0.0


def _pad_start_silence(wav, sr, pad_seconds=0.2):
    """Thêm một đoạn im lặng (silence) vào đầu file audio.
    Giúp chống hiện tượng nuốt chữ đầu khi phát trên các media player hoặc loa Bluetooth.
    """
    if pad_seconds <= 0:
        return wav
    
    pad_samples = int(pad_seconds * sr)
    silence = np.zeros(pad_samples, dtype=wav.dtype)
    return np.concatenate([silence, wav])


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


def _crossfade_concat(wav1, wav2, sr, fade_ms=10):
    """Nối 2 đoạn audio mượt mà (crossfade) để tránh tiếng click (lụp bụp) ở điểm nối."""
    if len(wav1) == 0: return wav2
    if len(wav2) == 0: return wav1
    
    fade_samples = int((fade_ms / 1000.0) * sr)
    fade_samples = min(fade_samples, len(wav1), len(wav2))
    
    if fade_samples <= 0:
        return np.concatenate([wav1, wav2])
        
    fade_out = np.linspace(1.0, 0.0, fade_samples)
    fade_in = np.linspace(0.0, 1.0, fade_samples)
    
    overlap1 = wav1[-fade_samples:] * fade_out
    overlap2 = wav2[:fade_samples] * fade_in
    mixed = overlap1 + overlap2
    
    return np.concatenate([wav1[:-fade_samples], mixed, wav2[fade_samples:]])


def _apply_dramatic_exclamation(wav, sr, raw_text):
    """
    Kéo dài và nâng tone tự động ở đầu hoặc cuối câu nếu phát hiện dấu '!!!'.
    Đúng chuẩn phong cách Theanh28:
    - 'Ôi!!!' ở đầu -> Kéo dài (time-stretch) và vút lên (pitch-shift).
    - '...ngay!!!' ở cuối -> Ngân dài chữ cuối và nâng tone CTA kêu gọi.
    """
    if "!!!" not in raw_text:
        return wav

    import librosa

    # Tìm đoạn có tiếng nói thật sự, dùng top_db=35 để dễ tách từ hơn
    intervals = librosa.effects.split(wav, top_db=35)
    if len(intervals) == 0:
        return wav
    
    start_idx = intervals[0][0]
    end_idx = intervals[-1][1]
    
    words = raw_text.strip().split()
    
    # Xác định vị trí có !!! (ở 2 chữ đầu hoặc 2 chữ cuối)
    elevate_start = any("!!!" in w for w in words[:2])
    elevate_end = any("!!!" in w for w in words[-2:])
    
    if not (elevate_start or elevate_end):
        return wav

    print("[Audio FX] Kích hoạt hiệu ứng tò mò/CTA (kéo dài + nâng tone) cho dấu '!!!'")
    
    # Tự động tìm ranh giới từ đầu tiên dựa vào khoảng lặng
    first_word_end = intervals[0][1]
    # Giới hạn tối đa 0.8s cho từ đầu tiên (tránh gom quá nhiều từ nếu nói lướt)
    if (first_word_end - start_idx) > 0.8 * sr:
        first_word_end = start_idx + int(0.5 * sr)
        
    # Tự động tìm ranh giới từ cuối cùng
    last_word_start = intervals[-1][0]
    if (end_idx - last_word_start) > 1.0 * sr:
        last_word_start = end_idx - int(0.6 * sr)
    
    if first_word_end > last_word_start:
        mid = (start_idx + end_idx) // 2
        first_word_end = mid
        last_word_start = mid
    
    pieces = []
    
    # 1. Khoảng lặng đầu
    pieces.append(wav[:start_idx])
    
    # 2. Từ đầu tiên (VD: Ôi!!!)
    first_word = wav[start_idx:first_word_end]
    if elevate_start and len(first_word) > 0:
        # Giảm tốc độ (kéo dài 25%) và nâng pitch 2.5 semitones
        first_word = librosa.effects.time_stretch(first_word, rate=0.8)
        first_word = librosa.effects.pitch_shift(first_word, sr=sr, n_steps=2.5, n_fft=512, hop_length=128)
    pieces.append(first_word)
    
    # 3. Đoạn giữa
    pieces.append(wav[first_word_end:last_word_start])
    
    # 4. Từ cuối cùng (VD: ngay!!!)
    last_word = wav[last_word_start:end_idx]
    if elevate_end and len(last_word) > 0:
        # Ngân dài (kéo dài 30%) và nâng pitch mạnh để kêu gọi CTA
        last_word = librosa.effects.time_stretch(last_word, rate=0.7)
        last_word = librosa.effects.pitch_shift(last_word, sr=sr, n_steps=3.0, n_fft=512, hop_length=128)
    pieces.append(last_word)
    
    # 5. Khoảng lặng cuối
    pieces.append(wav[end_idx:])
    
    # Nối các đoạn lại bằng crossfade để không bị vấp
    out_wav = pieces[0]
    for p in pieces[1:]:
        out_wav = _crossfade_concat(out_wav, p, sr, fade_ms=10)
        
    return out_wav


def generate_voice_clone(model, text, language, ref_audio, ref_text,
                         theanh28_style=False,
                         pitch_shift=None, custom_gen_config=None):
    """
    Generate speech using custom reference audio.
    
    Args:
        model: Loaded Qwen3TTSModel
        text: Text to synthesize
        language: Language identifier
        ref_audio: Path to reference audio file
        ref_text: Transcript of reference audio
        theanh28_style: If True, apply text manipulation (. → !! , → ! etc.)
                       for dramatic reading. Only from checkbox, never auto.
        pitch_shift: Semitones to shift pitch AFTER generation.
                    Only applied when explicitly set (e.g., from slider).
        custom_gen_config: Optional dict of generation config overrides.
    """
    text = normalize_vietnamese(text, theanh28_style=theanh28_style)
    # ref_text: chỉ chuẩn hóa cơ bản (KHÔNG dùng theanh28_style)
    # vì ref_text phải khớp chính xác với âm thanh trong file audio mẫu.
    # Nếu biến đổi ref_text (!!!, dấu câu...) → mismatch ICL → model mất định hướng → tiếng Trung
    ref_text = normalize_vietnamese(ref_text, theanh28_style=False)
    
    # Clean leading punctuation that user might have added
    import re
    text = re.sub(r'^[\s.,?!:;…]+', '', text)
    
    # Select generation config:
    # Standard config: uses lower temperature (see GENERATION_CONFIG above)
    gen_config = GENERATION_CONFIG.copy()
    print("[Config] Tham số chuẩn — nhiệt độ thấp để tránh giọng Trung")
    
    # Override with custom speaker-specific config if provided
    if custom_gen_config:
        gen_config.update(custom_gen_config)
        print("[Config] Áp dụng tham số tuỳ chỉnh riêng cho giọng")

    if theanh28_style:
        print("[Style] Nhấn nhá cảm xúc (. → !! , → ! ! → !!!)")

    print(f"[Language] Ngôn ngữ đầu ra: {language}")
    print(f"[Text] Nội dung (đã chuẩn hóa): {text[:80]}{'...' if len(text) > 80 else ''}")
    print(f"[Ref] Transcript mẫu (đã chuẩn hóa): {ref_text[:80]}{'...' if len(ref_text) > 80 else ''}")
    
    print("[Status] Đang tiến hành tạo giọng nói (có thể mất từ vài chục giây đến vài phút tùy độ dài)...")
    
    wavs, sr = model.generate_voice_clone(
        text=text,
        language=language,
        ref_audio=ref_audio,
        ref_text=ref_text,
        **gen_config,
    )
    
    result = wavs[0]
    

            
    # Thêm một chút khoảng lặng ở đầu để chống nuốt âm chữ đầu tiên do độ trễ của media player
    result = _pad_start_silence(result, sr, pad_seconds=0.2)

        
    # Tự động nhận diện và áp dụng hiệu ứng cho dấu !!! (Theanh28 style CTA)
    # Lưu ý: truyền raw text ban đầu để check chính xác dấu '!!!' do text_normalizer có thể biến đổi.
    # Nhưng vì normalization hiện tại giữ lại '!!!', chúng ta có thể dùng `text` hoặc raw argument.
    # Ở đây tôi truyền tham số text gốc (chưa qua warmup) nhưng đã normalize.
    if theanh28_style:
        result = _apply_dramatic_exclamation(result, sr, text)
    
    # Post-processing pitch shift — ONLY when explicitly requested.
    if pitch_shift and pitch_shift != 0:
        result = _pitch_shift_audio(result, sr, pitch_shift)
    
    return result, sr


def generate_with_speaker(model, text, language, speaker_key, ref_info, base_dir,
                          theanh28_style=False,
                          pitch_shift=None):
    """Generate speech using a built-in reference speaker."""
    if speaker_key not in ref_info:
        available = ", ".join(ref_info.keys())
        raise ValueError(f"Speaker '{speaker_key}' not found. Available: {available}")

    speaker = ref_info[speaker_key]
    ref_audio_path = os.path.join(base_dir, speaker["audio_path"])
    ref_text = speaker["text"]
    custom_gen_config = speaker.get("generation_config", None)

    return generate_voice_clone(
        model, text, language, ref_audio_path, ref_text,
        theanh28_style=theanh28_style,
        pitch_shift=pitch_shift,
        custom_gen_config=custom_gen_config
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
    # Checkbox --theanh28 → theanh28_style = True
    #   → Text manipulation (. → !! , → ! ! → !!! ? → ???)
    #   → Also enables optional pitch shift.
    # ─────────────────────────────────────────────────────────────────
    
    # Text manipulation: ONLY from checkbox (never auto)
    theanh28_style = args.theanh28

    if args.speaker:
        ref_info = load_speaker_info(ref_info_path)
        print(f"Generating with speaker: {ref_info[args.speaker]['name']}...")
        wav, sr = generate_with_speaker(
            model, args.text, args.language, args.speaker, ref_info, base_dir,
            theanh28_style=theanh28_style,
            pitch_shift=args.pitch_shift,
        )
    else:
        print(f"Generating with custom reference audio: {args.ref_audio}...")
        wav, sr = generate_voice_clone(
            model, args.text, args.language, args.ref_audio, args.ref_text,
            theanh28_style=theanh28_style,
            pitch_shift=args.pitch_shift,
        )

    sf.write(args.output, wav, sr)
    print(f"Saved to {args.output} (sample rate: {sr}Hz)")


if __name__ == "__main__":
    main()
