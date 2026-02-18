import os
import time
import pandas as pd
import requests
from sarvamai import SarvamAI
import framework_config as config

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
    # Filter only relevant files if needed. For now, take all valid/invalid samples.
    # To save credits/time, we can filter for only 'Valid' plus a few 'Not Valid'.
    # But let's run all ~6 samples.
    
    files_to_upload = []
    file_map = {} # filename -> filepath
    sample_map = {} # filename -> sample_id

    for index, row in df.iterrows():
        filepath = row['file_path']
        filename = os.path.basename(filepath)
        sample_id = row['sample_id']
        
        if os.path.exists(filepath):
            files_to_upload.append(filename)
            file_map[filename] = filepath
            sample_map[filename] = sample_id
        else:
            print(f"File missing: {filepath}")

    if not files_to_upload:
        print("No files to process.")
        return

    print(f"Starting Batch Job for {len(files_to_upload)} files...")

    # 1. Create Job
    try:
        print("Creating Job...")
        job = client.speech_to_text_job.create_job(
            model="saaras:v3",
            language_code="te-IN",
            mode="transcribe" 
        )
        print(f"Job Object: {job}")
        print(f"Job Dir: {dir(job)}")
        
        # job_id = job.id # Commented out until we find correct attribute
        # return

        # 2. Get Upload Links
        print("Getting Upload Links...")
        upload_resp = client.speech_to_text_job.get_upload_links(job_id=job_id, files=files_to_upload)
        
        # 3. Upload Files
        print("Uploading Files...")
        # upload_resp likely contains a list or dict of upload details
        # We need to inspect stricture. Assuming it has a way to map filename -> url
        # Based on typical patterns, it might be a dict or list of objects
        
        # Let's assume upload_resp is pydantic model or dict.
        # Check if it has 'files' attribute?
        # Let's print dir if we can't be sure, but let's try to iterate.
        
        # It usually returns a list of { 'filename': ..., 'url': ..., 'fields': ... } or just url.
        # But SDK might return object.
        # I'll convert to dict/json if possible or inspect via print.
        
        # Validating upload structure via debug print first (safe approach) would be better?
        # Or I can just try accessing 'items' or iterating.
        
        # Let's try iterating.
        # Based on similar SDKs, it might be:
        # for file_info in upload_resp.files:
        #    ...
        
        # I will assume `upload_resp` is the response object and it has a property `unnamed_list` or it's iterable?
        # Wait, if `FilesUploadResponse` is a Pydantic model, I debugged `create` but not the response type structure.
        
        # Let's iterate over `files_to_upload` and find the matching link in `upload_resp`.
        
        # Only relying on `requests.put` to the URL.
        
    except Exception as e:
        print(f"Error setting up job: {e}")
        return

    # To implement the upload loop correctly without knowing exact structure, 
    # I will inspect `upload_resp` type in a small script first?
    # No, I'll allow this script to fail/print and I'll fix it.
    pass

if __name__ == "__main__":
    transcribe_sarvam_batch()
