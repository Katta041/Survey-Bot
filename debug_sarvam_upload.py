import os
import time
from sarvamai import SarvamAI
import framework_config as config

def debug_upload():
    print("Initializing Sarvam AI Client...")
    try:
        client = SarvamAI(api_subscription_key=config.SARVAM_API_KEY)
    except Exception as e:
        print(f"Error initializing Sarvam Client: {e}")
        return

    # Pick one file (MP3 check)
    test_file = "/Users/aierarohit/Desktop/Political Data/audio_samples/Valid_45c3ab84-6136-4d54-9601-544bdb5d7c6d.mp3"
    if not os.path.exists(test_file):
        print(f"Test file not found: {test_file}")
        return

    print(f"Creating Test Job for 1 file: {test_file}")
    try:
        import requests
        job = client.speech_to_text_job.create_job(
            model="saaras:v3",
            language_code="te-IN",
            mode="transcribe" 
        )
        print(f"Job Created: {job.job_id}")
        
        print("Uploading file using SDK (Async wrapper internally)...")
        filename = os.path.basename(test_file)
        # The SDK uses asyncio/httpx internally for upload_files
        # Let's try calling it directly
        res = job.upload_files([test_file])
        print(f"SDK Upload Result: {res}")
        
        print("Waiting 5s for propagation...")
        time.sleep(5)
        
        status = job.get_status()
        print(f"Job Status: files={status.total_files}, state={status.job_state}")
        
        print("Manual Start with 'files' in body...")
        start_url = f"https://api.sarvam.ai/speech-to-text/job/v1/{job.job_id}/start"
        start_headers = {
            "api-subscription-key": config.SARVAM_API_KEY,
            "content-type": "application/json"
        }
        start_body = {
            "files": [filename] 
        }
        
        start_res = requests.post(start_url, headers=start_headers, json=start_body)
        print(f"Manual Start Status: {start_res.status_code}")
        print(f"Manual Start Resp: {start_res.text}")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
            
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_upload()
