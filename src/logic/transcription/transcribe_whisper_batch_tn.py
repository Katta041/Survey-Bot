import os
import time
import pandas as pd
import json
import openai
import framework_config as config
from concurrent.futures import ThreadPoolExecutor, as_completed

def transcribe_audio_whisper(filepath, sample_id, client):
    try:
        with open(filepath, "rb") as audio_file:
            # We use prompt to hint it's Tamil political context
            response = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                language="ta",
                prompt="தமிழ்நாடு அரசியல், தேர்தல், முதலமைச்சர், தி.மு.க, அ.தி.மு.க, த.வெ.க, விஜய்"
            )
            return sample_id, response.text, None
    except Exception as e:
        return sample_id, None, str(e)

def transcribe_whisper_batch_tn():
    tn_download_dir = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'tn_samples')
    metadata_path = os.path.join(tn_download_dir, 'tn_downloaded_metadata.csv')
    output_csv = os.path.join(tn_download_dir, 'tn_transcribed_metadata_whisper.csv')
    
    if not os.path.exists(metadata_path):
        print("Metadata file not found. Run TN downloader first.")
        return

    print("Initializing OpenAI Client...")
    try:
        client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
    except Exception as e:
        print(f"Error initializing OpenAI Client: {e}")
        return

    df = pd.read_csv(metadata_path)
    
    files_to_process = []
    for index, row in df.iterrows():
        filepath = row['file_path']
        sample_id = row['sample_id']
        
        if os.path.exists(filepath):
            files_to_process.append((filepath, sample_id))
        else:
            print(f"File missing: {filepath}")

    if not files_to_process:
        print("No files to process.")
        return

    total_files = len(files_to_process)
    print(f"Total files to process via Whisper API: {total_files}")
    
    transcripts = {}
    errors = {}
    success_count = 0

    # Process in parallel (Whisper API is quite fast, but rate limits apply)
    # Using 5 workers to be safe with rate limits
    print("--- STARTING TRANSCRIPTION ---")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_sample = {
            executor.submit(transcribe_audio_whisper, filepath, sample_id, client): sample_id 
            for filepath, sample_id in files_to_process
        }
        
        completed = 0
        for future in as_completed(future_to_sample):
            sample_id = future_to_sample[future]
            try:
                sid, text, error = future.result()
                if text:
                    transcripts[sid] = text
                    success_count += 1
                else:
                    transcripts[sid] = f"ERROR: {error}"
                    errors[sid] = error
            except Exception as e:
                 transcripts[sample_id] = f"EXCEPTION: {str(e)}"
                 errors[sample_id] = str(e)
            
            completed += 1
            if completed % 20 == 0 or completed == total_files:
                print(f"Processed {completed}/{total_files} files...")

    elapsed = time.time() - start_time
    print(f"\n--- TRANSCRIPTION COMPLETE ---")
    print(f"Time taken: {elapsed:.2f} seconds")
    print(f"Successful: {success_count}/{total_files}")
    
    if errors:
        print(f"Failed: {len(errors)}. Example errors: {list(errors.values())[:3]}")

    # Aggregation Phase
    df_transcripts = []
    
    for index, row in df.iterrows():
        sample_id = row['sample_id']
        transcript = transcripts.get(sample_id, "TRANSCRIPT_NOT_FOUND")
        df_transcripts.append(transcript)

    df['transcript'] = df_transcripts
    df.to_csv(output_csv, index=False)
    
    print(f"Saved {len(df)} records to {output_csv}")

if __name__ == "__main__":
    transcribe_whisper_batch_tn()
