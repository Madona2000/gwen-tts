from inference import load_model, load_speaker_info, generate_with_speaker
import soundfile as sf
import os
import torch
import librosa
import numpy as np

model_path = "g-group-ai-lab/gwen-tts-0.6B"
print("Loading model...")
model = load_model(model_path, device="cpu")

print("Loading speaker info...")
ref_info = load_speaker_info("data/ref_info.json")

# Let's temporarily override the config for this test
ref_info["vietcuong_ai"]["audio_path"] = "data/infer-audio/Vietcuong_AI.WAV" # use original
ref_info["vietcuong_ai"]["generation_config"] = {
    "temperature": 0.7,
    "top_k": 50,
    "top_p": 0.9,
    "repetition_penalty": 1.0,
    "subtalker_temperature": 0.7,
    "subtalker_top_k": 50,
    "subtalker_top_p": 0.9
}

text = "Chào bạn, đây là giọng đọc thử nghiệm để kiểm tra xem tôi có còn bị lèo nhèo hay giọng Trung Quốc không nhé."
print(f"Generating for text: {text}")

wav, sr = generate_with_speaker(
    model, 
    text=text, 
    language="vietnamese", 
    speaker_key="vietcuong_ai", 
    ref_info=ref_info, 
    base_dir="."
)

out_path = "data/infer-audio/Vietcuong_AI_test_high_temp.wav"
sf.write(out_path, wav, sr)
print(f"Saved to {out_path}")
