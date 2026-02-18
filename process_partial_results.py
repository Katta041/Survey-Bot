import os
import pandas as pd
import json
import framework_config as config

def process_partial_results():
    # 1. Load Master Metadata
    metadata_path = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'downloaded_metadata.csv')
    if not os.path.exists(metadata_path):
        print("Metadata file not found.")
        return

    df = pd.read_csv(metadata_path)
    print(f"Loaded master metadata with {len(df)} records.")

    # 2. Scan Output Directory
    output_dir = os.path.join(config.AUDIO_DOWNLOAD_DIR, "sarvam_outputs_chunked")
    if not os.path.exists(output_dir):
        print(f"Output directory {output_dir} does not exist.")
        return

    # Map filename -> transcript
    filename_to_transcript = {}
    
    # List all JSONs
    json_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
    print(f"Found {len(json_files)} JSON transcripts.")

    for json_file in json_files:
        path = os.path.join(output_dir, json_file)
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                
            # filename in JSON might be original input name or "input.mp3.json"
            # The script logic: input_fname = task.inputs[0].file_name
            # The saved filename is typically input_fname + ".json"
            
            # Reconstruct original filename
            # If saved as "file.mp3.json", original is "file.mp3"
            original_filename = json_file.replace(".json", "")
            
            if 'transcript' in data:
                 filename_to_transcript[original_filename] = data['transcript']
            else:
                 filename_to_transcript[original_filename] = "NO_TRANSCRIPT_KEY"
                 
        except Exception as e:
            print(f"Error reading {json_file}: {e}")

    # 3. Join with Master Data
    df_transcripts = []
    found_count = 0
    
    for index, row in df.iterrows():
        filepath = row['file_path']
        filename = os.path.basename(filepath)
        
        # Check direct map
        transcript = filename_to_transcript.get(filename)
        
        if not transcript:
             # Try other variations just in case
             # e.g. maybe json name doesn't match exactly?
             # For now, stick to simple match
             transcript = "PENDING"
        else:
            found_count += 1
            
        df_transcripts.append(transcript)

    df['transcript'] = df_transcripts
    
    # 4. Save Partial CSV
    output_csv = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'transcribed_metadata_sarvam_partial.csv')
    df.to_csv(output_csv, index=False)
    print(f"Saved partial results to {output_csv}")
    print(f"Matched {found_count}/{len(df)} records.")

if __name__ == "__main__":
    process_partial_results()
