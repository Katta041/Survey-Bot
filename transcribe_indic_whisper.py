import os
import pandas as pd
import torch
import av
import numpy as np
from transformers import pipeline
import framework_config as config

# Model ID for Specialized Telugu Whisper
MODEL_ID = "vasista22/whisper-telugu-tiny"

def load_audio_av_np(filepath):
    """Loads audio using PyAV, resamples to 16kHz, and returns numpy array."""
    try:
        container = av.open(filepath)
        audio_stream = container.streams.audio[0]
        
        # Whisper expects 16kHz mono
        resampler = av.AudioResampler(format='fltp', layout='mono', rate=16000)
        
        audio_frames = []
        for frame in container.decode(audio_stream):
            frame.pts = None
            resampled_frames = resampler.resample(frame)
            for r_frame in resampled_frames:
                audio_frames.append(r_frame.to_ndarray())
        
        resampled_frames = resampler.resample(None)
        if resampled_frames:
             for r_frame in resampled_frames:
                audio_frames.append(r_frame.to_ndarray())

        if not audio_frames:
             return None, None
             
        # Concatenate: av returns [channels, samples]
        audio_data = np.concatenate(audio_frames, axis=1)
        
        # Flatten to 1D
        if audio_data.shape[0] == 1:
            audio_data = audio_data.squeeze()
            
        return audio_data, 16000
    except Exception as e:
        print(f"AV Load Error for {filepath}: {e}")
        return None, None

def transcribe_indic_whisper():
    metadata_path = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'downloaded_metadata.csv')
    if not os.path.exists(metadata_path):
        print("Metadata file not found. Run downloader first.")
        return

    print(f"Loading Model Pipeline: {MODEL_ID}...")
    try:
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        # device = "cpu" # Failback
        print(f"Using device: {device}")
        
        # higher level pipeline, chunk_length_s=30
        transcriber = pipeline("automatic-speech-recognition", model=MODEL_ID, device=device, chunk_length_s=30)
    except Exception as e:
        print(f"Error loading pipeline: {e}")
        return

    df = pd.read_csv(metadata_path)
    print(f"Transcribing {len(df)} files...")

    transcripts = []

    for index, row in df.iterrows():
        filepath = row['file_path']
        sample_id = row['sample_id']
        
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            transcripts.append("ERROR: File not found")
            continue

        print(f"Transcribing {sample_id} ({row['ground_truth_validity']})...")
        
        try:
            # Load audio using AV
            audio_data, sample_rate = load_audio_av_np(filepath)
            
            if audio_data is None:
                raise Exception("Failed to load audio with AV")

            print(f"Audio Stats: Shape={audio_data.shape}, Range=[{audio_data.min()}, {audio_data.max()}]")
            
            # Pipeline accepts numpy array
            # Removed generate_kwargs={"language": "telugu"} to avoid config conflict
            result = transcriber(audio_data)
            text = result['text']
            
            print(f"Transcript: {text[:50]}...")
            transcripts.append(text)
            
        except Exception as e:
            print(f"Error transcribing {sample_id}: {e}")
            transcripts.append(f"ERROR: {str(e)}")

    # Save to a NEW metadata file
    df['transcript'] = transcripts
    output_csv = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'transcribed_metadata_indic_whisper.csv')
    df.to_csv(output_csv, index=False)
    print(f"Transcription complete. Saved to {output_csv}")

if __name__ == "__main__":
    transcribe_indic_whisper()
