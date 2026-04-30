import sys
import torch
import soundfile as sf
sys.path.insert(0, '.')
from qwen_tts.inference.qwen3_tts_model import Qwen3TTSForConditionalGeneration
from text_normalizer import normalize_vietnamese

model_path = "/Users/mac/.cache/huggingface/hub/models--g-group-ai-lab--gwen-tts-0.6B/snapshots/a83e1f08656d48217a83f0ad422d1610d5b5c963"
device = "mps" if torch.backends.mps.is_available() else "cpu"

print("Loading model...")
model = Qwen3TTSForConditionalGeneration.from_pretrained(model_path, device_map=device)

text = "Chào mừng các bạn đến với video ngày hôm nay. Hôm nay chúng ta sẽ tìm hiểu về cách sử dụng công nghệ."
text = normalize_vietnamese(text)

# We need a ref_audio and ref_text. Let's use 'theanh_28' as a custom clone test.
import json
with open('data/ref_info.json') as f:
    ref_info = json.load(f)

ref_audio = ref_info['theanh_28']['audio_path']
ref_text = normalize_vietnamese(ref_info['theanh_28']['text'])

print("Generating with high temp (0.7)...")
wav_high, sr = model.generate_voice_clone(
    text=text,
    language="vietnamese",
    ref_audio=ref_audio,
    ref_text=ref_text,
    temperature=0.7,
    subtalker_temperature=0.7,
    top_p=0.9,
    top_k=50,
    repetition_penalty=1.0
)
sf.write("test_high.wav", wav_high[0], sr)

print("Generating with low temp (0.3)...")
wav_low, sr = model.generate_voice_clone(
    text=text,
    language="vietnamese",
    ref_audio=ref_audio,
    ref_text=ref_text,
    temperature=0.3,
    subtalker_temperature=0.1,
    top_p=0.85,
    top_k=20,
    repetition_penalty=1.2
)
sf.write("test_low.wav", wav_low[0], sr)

print("Done.")
