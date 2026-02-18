import os
import pandas as pd
import torch
import av
import numpy as np
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
import framework_config as config

# Model ID
# Using a well-known Telugu Wav2Vec2 fine-tune
MODEL_ID = "anuragshas/wav2vec2-large-xlsr-53-telugu" 

def load_audio_av(filepath):
    """Loads audio using PyAV, resamples to 16kHz, and converts to torch tensor."""
    try:
        container = av.open(filepath)
        audio_stream = container.streams.audio[0]
        
        # Configure resampler for 16kHz mono
        resampler = av.AudioResampler(format='fltp', layout='mono', rate=16000)
        
        audio_frames = []
        for frame in container.decode(audio_stream):
            # Resample on the fly using AV's resampler
            frame.pts = None # Ignore PTS to avoid warning
            resampled_frames = resampler.resample(frame)
            for r_frame in resampled_frames:
                audio_frames.append(r_frame.to_ndarray())
        
        # Flush the resampler
        resampled_frames = resampler.resample(None)
        if resampled_frames:
             for r_frame in resampled_frames:
                audio_frames.append(r_frame.to_ndarray())

        if not audio_frames:
             return None, None
             
        # Concatenate all frames (they are [1, samples] or [samples])
        # av returns [1, samples] for mono usually
        audio_data = np.concatenate(audio_frames, axis=1) # Concatenate along time dimension
        
        return torch.from_numpy(audio_data), 16000
    except Exception as e:
        print(f"AV Load Error for {filepath}: {e}")
        return None, None

def transcribe_samples_indic():
    metadata_path = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'downloaded_metadata.csv')
    if not os.path.exists(metadata_path):
        print("Metadata file not found. Run downloader first.")
        return

    print(f"Loading Model: {MODEL_ID}...")
    try:
        processor = Wav2Vec2Processor.from_pretrained(MODEL_ID)
        model = Wav2Vec2ForCTC.from_pretrained(MODEL_ID)
    except Exception as e:
        print(f"Error loading model: {e}")
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
            waveform, sample_rate = load_audio_av(filepath)
            
            if waveform is None:
                raise Exception("Failed to load audio with AV")

            # Waveform should be [1, N]
            # Squeeze to 1D array for processor
            input_values = processor(waveform.squeeze().numpy(), return_tensors="pt", sampling_rate=16000).input_values

            # Inference
            with torch.no_grad():
                logits = model(input_values).logits

            # Decode
            predicted_ids = torch.argmax(logits, dim=-1)
            transcription = processor.batch_decode(predicted_ids)[0]
            
            print(f"Transcript: {transcription[:50]}...")
            transcripts.append(transcription)
            
        except Exception as e:
            print(f"Error transcribing {sample_id}: {e}")
            transcripts.append(f"ERROR: {str(e)}")

    # Save to a NEW metadata file for the validator to pick up
    df['transcript'] = transcripts
    output_csv = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'transcribed_metadata_indic.csv')
    df.to_csv(output_csv, index=False)
    print(f"Transcription complete. Saved to {output_csv}")

if __name__ == "__main__":
    transcribe_samples_indic()
