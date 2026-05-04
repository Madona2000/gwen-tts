from inference import load_model, load_speaker_info, generate_with_speaker
import soundfile as sf
import os

model_path = "g-group-ai-lab/gwen-tts-0.6B"
print("Loading model...")
model = load_model(model_path, device="mps")

print("Loading speaker info...")
ref_info = load_speaker_info("data/ref_info.json")

text = "Xin chào, đây là một bài kiểm tra giọng đọc Việt Cường. Tôi sẽ cố gắng giữ được ngữ điệu trầm và sâu lắng, không bị mất dấu hay đọc giống người nước ngoài."
print(f"Generating for text: {text}")

wav, sr = generate_with_speaker(
    model, 
    text=text, 
    language="vietnamese", 
    speaker_key="vietcuong_ai", 
    ref_info=ref_info, 
    base_dir="."
)

out_path = "test_vietcuong_infer.wav"
sf.write(out_path, wav, sr)
print(f"Saved to {out_path}")
