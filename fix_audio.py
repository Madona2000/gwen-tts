import librosa
import soundfile as sf
import numpy as np

# Load audio
wav, sr = librosa.load("data/ref_audio/Vietcuong_AI.WAV", sr=None)
print(f"Original Length: {len(wav)/sr:.2f}s")

# Find non-silent intervals with a stricter top_db to remove more noise
intervals = librosa.effects.split(wav, top_db=25)
if len(intervals) > 0:
    start = intervals[0][0]
    end = intervals[-1][1]
    
    # 30ms pad
    pad = int(0.03 * sr)
    start = max(0, start - pad)
    end = min(len(wav), end + pad)
    
    trimmed_wav = wav[start:end]
    
    # Save it back
    sf.write("data/ref_audio/Vietcuong_AI_trimmed.WAV", trimmed_wav, sr)
    print(f"Trimmed from {start} to {end}. Length: {len(trimmed_wav)/sr:.2f}s")
else:
    print("No speech detected.")
