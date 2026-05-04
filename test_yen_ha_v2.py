from inference import load_model, load_speaker_info, generate_with_speaker
import soundfile as sf
import os

model_path = "g-group-ai-lab/gwen-tts-0.6B"
print("Loading model...")
model = load_model(model_path, device="cpu")

print("Loading speaker info...")
ref_info = load_speaker_info("data/ref_info.json")

text = "Xin chào các bạn, tôi đang thử nghiệm giọng đọc mới với âm điệu tự nhiên và có chiều sâu hơn. Bạn thấy sao?"

# Test Yến Nhi
print("Testing Yen Nhi...")
wav, sr = generate_with_speaker(
    model, 
    text=text, 
    language="vietnamese", 
    speaker_key="yen_nhi", 
    ref_info=ref_info, 
    base_dir="."
)
out_path = "data/infer-audio/yen_nhi_16k_v2_test.wav"
sf.write(out_path, wav, sr)
print(f"Saved Yen Nhi to {out_path}")

# Test NSND Hà Phương
print("Testing NSND Ha Phuong...")
wav, sr = generate_with_speaker(
    model, 
    text=text, 
    language="vietnamese", 
    speaker_key="nsnd_ha_phuong", 
    ref_info=ref_info, 
    base_dir="."
)
out_path = "data/infer-audio/nsnd_ha_phuong_16k_v2_test.wav"
sf.write(out_path, wav, sr)
print(f"Saved NSND Ha Phuong to {out_path}")
