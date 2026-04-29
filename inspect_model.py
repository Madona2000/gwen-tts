import sys
sys.path.insert(0, '.')
from qwen_tts import Qwen3TTSModel
import torch
print("Loading model...")
model = Qwen3TTSModel.from_pretrained('g-group-ai-lab/gwen-tts-0.6B', device_map='cpu')
print("Supported languages:", model._supported_languages_set())
print("Supported speakers:", model._supported_speakers_set())
