import librosa
import soundfile as sf
import numpy as np

# Load audio
wav, sr = librosa.load("data/ref_audio/Vietcuong_AI.WAV", sr=None)

# Find non-silent intervals
intervals = librosa.effects.split(wav, top_db=30)
if len(intervals) > 0:
    # Get the start of the first interval and end of the last
    start = intervals[0][0]
    end = intervals[-1][1]
    
    # Add a small pad (e.g. 50ms) to avoid cutting too abruptly
    pad = int(0.05 * sr)
    start = max(0, start - pad)
    end = min(len(wav), end + pad)
    
    trimmed_wav = wav[start:end]
    
    # Save it back
    sf.write("data/ref_audio/Vietcuong_AI_trimmed.WAV", trimmed_wav, sr)
    print(f"Trimmed from {start} to {end}. Original length: {len(wav)}, New length: {len(trimmed_wav)}")
else:
    print("No speech detected.")
