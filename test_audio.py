import librosa
import soundfile as sf
import sys

wav, sr = librosa.load("data/ref_audio/Vietcuong_AI.WAV", sr=None)
print("Duration:", librosa.get_duration(y=wav, sr=sr))
intervals = librosa.effects.split(wav, top_db=30)
print("Intervals:", intervals)
