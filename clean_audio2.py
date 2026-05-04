import librosa
import soundfile as sf

path = 'data/infer-audio/Vietcuong_AI.WAV'
y, sr = librosa.load(path, sr=24000)

# Trim leading and trailing silence more aggressively for the reference
y_trimmed, index = librosa.effects.trim(y, top_db=25)

# Save the cleaned file without volume normalization
sf.write('data/infer-audio/Vietcuong_AI_clean.wav', y_trimmed, sr)
print("Cleaned audio saved without normalization.")
