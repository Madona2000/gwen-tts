import librosa
import soundfile as sf
import os

def clean_and_resample(input_path, output_path, target_sr=16000):
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return
        
    print(f"Processing {input_path}...")
    # Load and resample to target_sr
    y, sr = librosa.load(input_path, sr=target_sr)
    
    # Trim silence
    y_trimmed, index = librosa.effects.trim(y, top_db=25)
    
    # Normalize volume
    y_normalized = librosa.util.normalize(y_trimmed)
    
    # Save
    sf.write(output_path, y_normalized, sr)
    print(f"Saved {output_path}. Orig len: {len(y)/sr:.2f}s, New len: {len(y_normalized)/sr:.2f}s")

# For Yến Nhi (try yen_nhi_fixed.wav if yen_nhi.wav doesn't exist)
yen_nhi_input = "data/ref_audio/yen_nhi.wav"
if not os.path.exists(yen_nhi_input):
    yen_nhi_input = "data/ref_audio/yen_nhi_fixed.wav"
clean_and_resample(yen_nhi_input, "data/ref_audio/yen_nhi_16k.wav")

# For NSND Hà Phương
nsnd_ha_phuong_input = "data/ref_audio/nsnd_ha_phuong.wav"
clean_and_resample(nsnd_ha_phuong_input, "data/ref_audio/nsnd_ha_phuong_16k.wav")
