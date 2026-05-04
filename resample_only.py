import librosa
import soundfile as sf
import os

def resample_only(input_path, output_path, target_sr=16000):
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return
        
    print(f"Processing {input_path}...")
    # Load and resample to target_sr
    y, sr = librosa.load(input_path, sr=target_sr)
    
    # Do NOT trim, just normalize the volume slightly to avoid clipping
    y_normalized = librosa.util.normalize(y)
    
    # Save
    sf.write(output_path, y_normalized, sr)
    print(f"Saved {output_path}. New length: {len(y_normalized)/sr:.2f}s")

resample_only("data/ref_audio/yen_nhi_fixed.wav", "data/ref_audio/yen_nhi_16k_v2.wav")
resample_only("data/ref_audio/nsnd_ha_phuong_fixed.wav", "data/ref_audio/nsnd_ha_phuong_16k_v2.wav")
