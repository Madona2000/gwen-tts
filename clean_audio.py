import librosa
import soundfile as sf
import numpy as np

# Load the file
path = 'data/infer-audio/Vietcuong_AI.WAV'
y, sr = librosa.load(path, sr=16000)

# Trim leading and trailing silence more aggressively for the reference
y_trimmed, index = librosa.effects.trim(y, top_db=25)

# Normalize volume
y_normalized = librosa.util.normalize(y_trimmed)

# Save the cleaned file
sf.write('data/ref_audio/vietcuong_ai_16k.wav', y_normalized, sr)
print(f"Cleaned audio saved. Original length: {len(y)/sr:.2f}s, New length: {len(y_normalized)/sr:.2f}s")
