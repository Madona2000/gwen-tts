import json
from inference import load_model, generate_with_speaker
import soundfile as sf
import os

print("Loading model...")
model = load_model("g-group-ai-lab/gwen-tts-0.6B")
with open("data/ref_info.json", "r", encoding="utf-8") as f:
    ref_info = json.load(f)

text = "Chào bạn, mình là trợ lý ảo, rất vui được gặp bạn."
print("Generating audio...")
wav, sr = generate_with_speaker(
    model=model,
    text=text,
    language="vietnamese",
    speaker_key="vietcuong_ai",
    ref_info=ref_info,
    base_dir="."
)
sf.write("Vietcuong_AI_test_0.5.wav", wav, sr)
print("Saved to Vietcuong_AI_test_0.5.wav")
