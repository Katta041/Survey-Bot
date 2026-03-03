import av
import io
import os
import pandas as pd
from sarvamai import SarvamAI
import framework_config as config

def load_audio_wav_bytes(filepath):
    """Loads audio using PyAV and converts to WAV bytes."""
    try:
        # Open the file with PyAV
        container = av.open(filepath)
        audio_stream = container.streams.audio[0]
        
        # Resample to 16kHz mono
        resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
        
        # Output buffer
        output_buffer = io.BytesIO()
        
        # Create a WAV container for the output buffer
        output_container = av.open(output_buffer, mode='w', format='wav')
        # Pass layout='mono' to add_stream
        output_stream = output_container.add_stream('pcm_s16le', rate=16000, layout='mono')
        # output_stream.channels = 1 # Removed logic causing error
        
        for frame in container.decode(audio_stream):
            frame.pts = None
            resampled_frames = resampler.resample(frame)
            for r_frame in resampled_frames:
                for packet in output_stream.encode(r_frame):
                    output_container.mux(packet)
                    
        # Flush
        resampled_frames = resampler.resample(None)
        if resampled_frames:
             for r_frame in resampled_frames:
                for packet in output_stream.encode(r_frame):
                    output_container.mux(packet)

        for packet in output_stream.encode(None): # Flush stream
            output_container.mux(packet)
            
        output_container.close()
        return output_buffer.getvalue()
        
    except Exception as e:
        print(f"AV Conversion Error for {filepath}: {e}")
        return None

def transcribe_sarvam():
    metadata_path = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'downloaded_metadata.csv')
    if not os.path.exists(metadata_path):
        print("Metadata file not found. Run downloader first.")
        return

    print("Initializing Sarvam AI Client...")
    try:
        # Correct init argument based on inspection
        client = SarvamAI(api_subscription_key=config.SARVAM_API_KEY)
    except Exception as e:
        print(f"Error initializing Sarvam Client: {e}")
        return

    df = pd.read_csv(metadata_path)
    print(f"Transcribing {len(df)} files with Sarvam AI...")

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
            # Convert to WAV bytes first
            wav_bytes = load_audio_wav_bytes(filepath)
            
            if wav_bytes is None:
                raise Exception("Failed to convert audio to WAV")

            # Sarvam AI Speech To Text
            result = client.speech_to_text.transcribe(
                file=wav_bytes, # Passing bytes
                model="saaras:v3", # Using Valid Model
                language_code="te-IN", 
                mode="transcribe"
            )
            
            transcript = result.transcript
            print(f"Transcript: {transcript[:50]}...")
            transcripts.append(transcript)
            
        except Exception as e:
            print(f"Error transcribing {sample_id}: {e}")
            transcripts.append(f"ERROR: {str(e)}")

    # Save to a NEW metadata file
    df['transcript'] = transcripts
    output_csv = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'transcribed_metadata_sarvam.csv')
    df.to_csv(output_csv, index=False)
    print(f"Transcription complete. Saved to {output_csv}")

if __name__ == "__main__":
    transcribe_sarvam()
