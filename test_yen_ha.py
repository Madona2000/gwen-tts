from inference import load_model, load_speaker_info, generate_with_speaker
import soundfile as sf
import os

model_path = "g-group-ai-lab/gwen-tts-0.6B"
print("Loading model...")
model = load_model(model_path, device="cpu")

print("Loading speaker info...")
ref_info = load_speaker_info("data/ref_info.json")

test_text = "Thật tuyệt vời! Mọi vấn đề về phát âm tiếng Việt đã được xử lý triệt để. Giờ đây tôi có thể đọc rành mạch, rõ chữ và tròn vành rõ chữ."

# Test Yến Nhi
print(f"Generating for Yến Nhi: {test_text}")
wav1, sr1 = generate_with_speaker(
    model, 
    text=test_text, 
    language="vietnamese", 
    speaker_key="yen_nhi", 
    ref_info=ref_info, 
    base_dir="."
)
out_path1 = "data/infer-audio/yen_nhi_16k_test.wav"
sf.write(out_path1, wav1, sr1)
print(f"Saved Yến Nhi test to {out_path1}")

# Test NSND Hà Phương
print(f"Generating for NSND Hà Phương: {test_text}")
wav2, sr2 = generate_with_speaker(
    model, 
    text=test_text, 
    language="vietnamese", 
    speaker_key="nsnd_ha_phuong", 
    ref_info=ref_info, 
    base_dir="."
)
out_path2 = "data/infer-audio/nsnd_ha_phuong_16k_test.wav"
sf.write(out_path2, wav2, sr2)
print(f"Saved NSND Hà Phương test to {out_path2}")
