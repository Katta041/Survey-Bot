import os
import json
from sarvamai import SarvamAI
import framework_config as config

# JOB_ID = "20260217_dee27ec3-7864-4e6e-8ac0-0e6a34672fe2" # Old Job
JOB_ID = "20260217_814cfd0c-608a-4112-abba-6cef09e2eec3" # Latest Job (Manual Upload)

def retrieve_job():
    print("Initializing Sarvam AI Client...")
    try:
        client = SarvamAI(api_subscription_key=config.SARVAM_API_KEY)
    except Exception as e:
        print(f"Error initializing Sarvam Client: {e}")
        return

    print(f"Retrieving Job {JOB_ID}...")
    try:
        # Get Job Status
        # job = client.speech_to_text_job.get_job(job_id=JOB_ID)
        # print("Job Status:", job.status) # Assuming field exists
        
        # Get Results
        job = client.speech_to_text_job.get_job(job_id=JOB_ID)
        print("Job Status:", job.get_status())
        
        # Download Outputs
        output_dir = "/Users/aierarohit/Desktop/Political Data/sarvam_outputs"
        job.download_outputs(output_dir=output_dir)
        print(f"Downloaded outputs to {output_dir}")

        # Get results structure for mapping
        results = job.get_file_results()
        
        # Parse one file to see structure
        if 'successful' in results and results['successful']:
            first_item = results['successful'][0]
            output_filename = first_item['output_file'] # e.g. 0.json
            output_path = os.path.join(output_dir, output_filename)
            
            if os.path.exists(output_path):
                with open(output_path, 'r') as f:
                    data = json.load(f)
                    print(f"Content of {output_filename}:", data)
                    # Check for transcript
                    if 'transcript' in data:
                        print("TRANSCRIPT FOUND!")
            else:
                print(f"Output file {output_path} missing.")


        # The previous script used job.get_file_results().
        # If I get the job object, does it have that method? 
        # Inspecting dir(results) will tell.
        
        # Also try client method if job object logic was wrong in my head (though inspection said create_job returns Job object which has methods).
        # But get_job returns what? Likely a Job object too.
        
    except Exception as e:
        print(f"Error retrieving job: {e}")

if __name__ == "__main__":
    retrieve_job()
