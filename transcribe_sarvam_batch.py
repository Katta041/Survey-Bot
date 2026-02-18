import os
import time
import pandas as pd
import json
import requests
from sarvamai import SarvamAI
from sarvamai.speech_to_text_job.job import SpeechToTextJob
import framework_config as config
import sys

# Sarvam limit
CHUNK_SIZE = 20 

def transcribe_sarvam_batch():
    metadata_path = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'downloaded_metadata.csv')
    if not os.path.exists(metadata_path):
        print("Metadata file not found. Run downloader first.")
        return

    print("Initializing Sarvam AI Client...")
    try:
        client = SarvamAI(api_subscription_key=config.SARVAM_API_KEY)
    except Exception as e:
        print(f"Error initializing Sarvam Client: {e}")
        return

    df = pd.read_csv(metadata_path)
    
    files_to_process = []
    # Map filename -> sample_id for quick lookup
    sample_map = {} 

    for index, row in df.iterrows():
        filepath = row['file_path']
        filename = os.path.basename(filepath)
        sample_id = row['sample_id']
        
        if os.path.exists(filepath):
            files_to_process.append(filepath)
            sample_map[filename] = sample_id
        else:
            print(f"File missing: {filepath}")

    if not files_to_process:
        print("No files to process.")
        return

    total_files = len(files_to_process)
    print(f"Total files to process: {total_files}")
    
    # Chunking
    chunks = [files_to_process[i:i + CHUNK_SIZE] for i in range(0, len(files_to_process), CHUNK_SIZE)]
    print(f"Split into {len(chunks)} chunks of size {CHUNK_SIZE} (max).")

    submitted_jobs = []

    # 1. Submission Phase
    print("--- SUBMISSION PHASE ---")
    for i, chunk in enumerate(chunks):
        print(f"\nProcessing Chunk {i+1}/{len(chunks)} ({len(chunk)} files)...")
        
        try:
            # Create Job
            job = client.speech_to_text_job.create_job(
                model="saaras:v3",
                language_code="te-IN",
                mode="transcribe" 
            )
            print(f"  Job Created: {job.job_id}")
            
            # Upload (SDK)
            print("  Uploading...")
            upload_res = job.upload_files(chunk)
            if not upload_res:
                print("  Upload reported failure False")

            # Start (Manual)
            print("  Starting (Manual)...")
            start_url = f"https://api.sarvam.ai/speech-to-text/job/v1/{job.job_id}/start"
            start_headers = {
                "api-subscription-key": config.SARVAM_API_KEY,
                "content-type": "application/json"
            }
            filenames = [os.path.basename(f) for f in chunk]
            start_body = {"files": filenames}
            
            start_res = requests.post(start_url, headers=start_headers, json=start_body)
            
            if start_res.status_code not in [200, 201]:
                print(f"  FAILED to start chunk {i+1}: {start_res.status_code} - {start_res.text}")
                continue # Skip adding to submitted list
            
            print("  Job Started.")
            submitted_jobs.append({
                'job_id': job.job_id,
                'files': chunk,
                'chunk_idx': i
            })
            
            # Rate limit buffer
            time.sleep(1) 
            
        except Exception as e:
            print(f"  Exception in chunk {i+1}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n--- SUBMISSION COMPLETE. {len(submitted_jobs)} jobs running. ---")
    
    # 2. Polling Phase
    print("--- POLLING PHASE ---")
    
    # Map filename -> transcript
    all_transcripts = {}
    
    # Track completion
    completed_jobs = set()
    output_dir = os.path.join(config.AUDIO_DOWNLOAD_DIR, "sarvam_outputs_chunked")
    os.makedirs(output_dir, exist_ok=True)

    while len(completed_jobs) < len(submitted_jobs):
        print(f"Status: {len(completed_jobs)}/{len(submitted_jobs)} jobs completed...")
        
        for job_pkg in submitted_jobs:
            jid = job_pkg['job_id']
            if jid in completed_jobs:
                continue
            
            # Check Status
            try:
                # Re-instantiate job object (lightweight)
                # job_obj = client.speech_to_text_job.get_job(jid) 
                # OR manual request to save instantiation overhead, but SDK is fine
                # let's use SDK for consistency
                job_obj = SpeechToTextJob(job_id=jid, client=client.speech_to_text_job)
                
                status = job_obj.get_status()
                state = status.job_state.lower()
                
                if state in ['completed', 'failed']:
                    print(f"  Job {jid} finished with state: {state}")
                    
                    if state == 'completed':
                        # Download
                        job_obj.download_outputs(output_dir)
                        
                        # Process results immediately
                        if hasattr(status, 'job_details'):
                            for task in status.job_details:
                                if not task.inputs: continue
                                input_fname = task.inputs[0].file_name
                                
                                # Find output
                                out_fname = task.outputs[0].file_name if task.outputs else input_fname + ".json"
                                out_path = os.path.join(output_dir, out_fname)
                                
                                if not os.path.exists(out_path):
                                    # Fallback check
                                    out_path = os.path.join(output_dir, input_fname + ".json")
                                
                                if os.path.exists(out_path):
                                    try:
                                        with open(out_path, 'r') as f:
                                            data = json.load(f)
                                            if 'transcript' in data:
                                                all_transcripts[input_fname] = data['transcript']
                                            else:
                                                all_transcripts[input_fname] = ""
                                    except:
                                        all_transcripts[input_fname] = "READ_ERROR"
                                else:
                                     all_transcripts[input_fname] = "OUTPUT_MISSING"
                    else:
                        print(f"  Job {jid} FAILED. Error: {status.error_message}")
                        
                    completed_jobs.add(jid)
                else:
                    # Still pending/running
                    pass
                    
            except Exception as e:
                print(f"Error polling job {jid}: {e}")
                # Don't mark as complete, retry next loop
        
        time.sleep(10) # 10s poll interval

    print("\n--- PROCESSING COMPLETE ---")
    
    # 3. Aggregation Phase
    df_transcripts = []
    success_count = 0
    
    for index, row in df.iterrows():
        filepath = row['file_path']
        filename = os.path.basename(filepath)
        
        transcript = all_transcripts.get(filename, "TRANSCRIPT_NOT_FOUND")
        df_transcripts.append(transcript)
        
        if transcript and transcript != "TRANSCRIPT_NOT_FOUND" and "ERROR" not in transcript:
            success_count += 1

    df['transcript'] = df_transcripts
    output_csv = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'transcribed_metadata_sarvam.csv')
    df.to_csv(output_csv, index=False)
    
    print(f"Saved {len(df)} records ({success_count} successful) to {output_csv}")

if __name__ == "__main__":
    transcribe_sarvam_batch()
