"""Test giọng An Nhi — câu chuẩn kiểm tra thanh điệu"""
import sys
sys.path.insert(0, ".")

from inference import load_model, generate_with_speaker, load_speaker_info
import soundfile as sf
from pathlib import Path

MODEL_PATH = "g-group-ai-lab/gwen-tts-0.6B"
DEVICE = "mps"

TEXT = "Hôm nay chúng ta sẽ cùng nhau khám phá một chủ đề vô cùng thú vị và bổ ích."
OUTPUT = "test_an_nhi.wav"

base_dir = Path(__file__).parent
ref_info = load_speaker_info(base_dir / "data" / "ref_info.json")

print("Loading model...")
model = load_model(MODEL_PATH, device=DEVICE)
print("Model loaded.")

print(f"Generating: {TEXT}")
wav, sr = generate_with_speaker(
    model, TEXT, "vietnamese", "an_nhi", ref_info, base_dir
)

sf.write(OUTPUT, wav, sr)
print(f"✅ Saved: {OUTPUT} ({sr}Hz)")
