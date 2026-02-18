import sarvamai
import inspect

print("Dir(sarvamai):", dir(sarvamai))
try:
    print("Help(sarvamai.SarvamAI):")
    print(help(sarvamai.SarvamAI))
    print("Signature:", inspect.signature(sarvamai.SarvamAI))
    
    # Try to init and inspect speech_to_text_job
    client = sarvamai.SarvamAI(api_subscription_key="test")
    if hasattr(client, 'speech_to_text_job'):
        print("SpeechToTextJob Dir:", dir(client.speech_to_text_job))
        if hasattr(client.speech_to_text_job, 'create_job'):
             print("CreateJob Sig:", inspect.signature(client.speech_to_text_job.create_job))
        if hasattr(client.speech_to_text_job, 'get_upload_links'):
             print("GetUploadLinks Sig:", inspect.signature(client.speech_to_text_job.get_upload_links))


    
except Exception as e:
    print(f"Error inspecting SarvamAI: {e}")
