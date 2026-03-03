import torchaudio
import torch
import av
import os

filepath = "/Users/aierarohit/Desktop/Political Data/audio_samples/Valid_4097eb5d-9bfd-43ad-b6fa-d30160f54301.mp3"

print("--- Torchaudio Info ---")
print(f"Available Backends: {torchaudio.list_audio_backends()}")
try:
    print(f"Current Backend: {torchaudio.get_audio_backend()}")
except:
    print("Could not get current backend (might be empty)")

print(f"\n--- Attempting Torchaudio Load: {filepath} ---")
try:
    waveform, sample_rate = torchaudio.load(filepath)
    print(f"Success! Shape: {waveform.shape}, SR: {sample_rate}")
except Exception as e:
    print(f"Torchaudio Load Failed: {e}")

print(f"\n--- Attempting AV Direct Load: {filepath} ---")
try:
    container = av.open(filepath)
    print(f"Container: {container}")
    print(f"Streams: {container.streams.audio}")
    
    # decode first frame
    for frame in container.decode(audio=0):
        print(f"Decoded Frame: {frame}")
        break
    print("AV Load Success")
except Exception as e:
    print(f"AV Load Failed: {e}")
