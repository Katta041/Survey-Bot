import os
import pandas as pd
from openai import OpenAI
import framework_config as config

client = OpenAI(api_key=config.OPENAI_API_KEY)

def transcribe_enhanced_whisper():
    # Load ENHANCED metadata
    metadata_path = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'enhanced_metadata.csv')
    if not os.path.exists(metadata_path):
        print("Enhanced metadata file not found. Run enhance_audio.py first.")
        return

    df = pd.read_csv(metadata_path)
    print(f"Transcribing {len(df)} enhanced files using Whisper API...")

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
            with open(filepath, "rb") as audio_file:
                # Using Whisper API with auto-detect language
                # We can add prompt="This is a Telugu survey." if needed to guide it
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    # language="te", # API rejected 'te'. Relying on prompt.
                    prompt="This is a Telugu political survey. The audio is in Telugu. Transcribe in Telugu script."
                )
            text = transcript.text
            print(f"Transcript: {text[:50]}...")
            transcripts.append(text)
            
        except Exception as e:
            print(f"Error transcribing {sample_id}: {e}")
            transcripts.append(f"ERROR: {str(e)}")

    # Save to a NEW metadata file for the validator
    df['transcript'] = transcripts
    output_csv = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'transcribed_metadata_enhanced.csv')
    df.to_csv(output_csv, index=False)
    print(f"Transcription complete. Saved to {output_csv}")

if __name__ == "__main__":
    transcribe_enhanced_whisper()
