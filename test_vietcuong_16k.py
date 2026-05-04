import os
import sys

sys.path.append('.')
from inference import synthesize_speech

def test():
    voice = "vietcuong_ai"
    text = "Xin chào, đây là một bài kiểm tra giọng đọc Việt Cường. Tôi sẽ cố gắng giữ được ngữ điệu trầm và sâu lắng, không bị mất dấu hay đọc giống người nước ngoài."
    
    print(f"Testing voice: {voice}")
    output_file = f"test_{voice}_16k.wav"
    try:
        synthesize_speech(text, voice, output_path=output_file)
        print(f"Success! Output saved to {output_file}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
