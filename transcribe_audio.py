import os
import pandas as pd
from openai import OpenAI
import framework_config as config

client = OpenAI(api_key=config.OPENAI_API_KEY)

def transcribe_samples():
    metadata_path = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'downloaded_metadata.csv')
    if not os.path.exists(metadata_path):
        print("Metadata file not found. Run downloader first.")
        return

    df = pd.read_csv(metadata_path)
    print(f"Transcribing {len(df)} files...")

    transcripts = []

    for index, row in df.iterrows():
        filepath = row['file_path']
        sample_id = row['sample_id']
        
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            transcripts.append("")
            continue

        print(f"Transcribing {sample_id} ({row['ground_truth_validity']})...")
        
        try:
            with open(filepath, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    # language="te" # Removing explicit language to test auto-detect
                )
            text = transcript.text
            print(f"Transcript: {text[:50]}...")
            transcripts.append(text)
        except Exception as e:
            print(f"Error transcribing {sample_id}: {e}")
            transcripts.append(f"ERROR: {str(e)}")

    df['transcript'] = transcripts
    df.to_csv(os.path.join(config.AUDIO_DOWNLOAD_DIR, 'transcribed_metadata.csv'), index=False)
    print("Transcription complete. Saved to transcribed_metadata.csv")

if __name__ == "__main__":
    transcribe_samples()
