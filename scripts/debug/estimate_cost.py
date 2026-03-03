import os
import pandas as pd
import math
import framework_config as config

def estimate_pipeline_cost(num_files=5000):
    # --- 1. Audio Duration Estimation (Sarvam API) ---
    # We need to find the average duration of our existing samples to extrapolate.
    tn_dir = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'tn_samples')
    metadata_path = os.path.join(tn_dir, "tn_downloaded_metadata.csv")
    
    avg_duration_minutes = 2.0 # Fallback estimate if we can't calculate
    
    # We don't have exact duration in metadata, but we can estimate from file size
    # 32kbps MP3 is roughly 4KB per second. 
    # Let's inspect the directory sizes to get average size.
    if os.path.exists(tn_dir):
        total_size = 0
        file_count = 0
        for f in os.listdir(tn_dir):
            if f.endswith('.mp3') or f.endswith('.mp4'):
                total_size += os.path.getsize(os.path.join(tn_dir, f))
                file_count += 1
        
        if file_count > 0:
            avg_size_bytes = total_size / file_count
            # Rough estimate: ~24kbps audio = ~3000 bytes/sec
            avg_duration_sec = avg_size_bytes / 3000
            avg_duration_minutes = avg_duration_sec / 60
            print(f"Estimated average audio duration from {file_count} files: {avg_duration_minutes:.2f} mins/file")

    total_audio_minutes = avg_duration_minutes * num_files
    total_audio_hours = total_audio_minutes / 60

    # Sarvam Saaras v3 pricing: 30 INR per hour (without diarization)
    sarvam_cost_inr = total_audio_hours * 30
    sarvam_cost_usd = sarvam_cost_inr / 83.0 # approx exchange rate

    # --- 2. LLM Token Estimation (GPT-4o API) ---
    # System prompt is ~350 tokens
    # User content (transcript + data) is roughly ~400 tokens on average for 2 mins of speech
    # Total input: ~750 tokens
    # Total output: JSON response ~50 tokens
    avg_input_tokens = 750
    avg_output_tokens = 50

    total_input_tokens = avg_input_tokens * num_files
    total_output_tokens = avg_output_tokens * num_files

    # GPT-4o Pricing: $2.50 / 1M input, $10.00 / 1M output
    gpt4o_input_cost = (total_input_tokens / 1_000_000) * 2.50
    gpt4o_output_cost = (total_output_tokens / 1_000_000) * 10.00
    total_gpt4o_cost_usd = gpt4o_input_cost + gpt4o_output_cost

    # Total Cost
    total_pipeline_cost_usd = sarvam_cost_usd + total_gpt4o_cost_usd

    print("\n" + "="*50)
    print(f"COST ESTIMATION FOR {num_files} AUDIO FILES (Tamil Nadu Pipeline)")
    print("="*50)
    
    print("\n1. Sarvam AI (Speech-to-Text: saaras:v3)")
    print(f"  - Average Audio Length: {avg_duration_minutes:.2f} minutes")
    print(f"  - Total Audio Processed: {total_audio_hours:.2f} hours")
    print(f"  - Pricing: ₹30 INR per hour")
    print(f"  - Total Sarvam Cost: ₹{sarvam_cost_inr:.2f} INR (approx ${sarvam_cost_usd:.2f} USD)")

    print("\n2. OpenAI (Classification: gpt-4o)")
    print(f"  - Est. Input Tokens per file: ~{avg_input_tokens}")
    print(f"  - Est. Output Tokens per file: ~{avg_output_tokens}")
    print(f"  - Total M-Tokens: {total_input_tokens/1e6:.2f}M In, {total_output_tokens/1e6:.2f}M Out")
    print(f"  - Pricing: $2.50/1M In, $10.00/1M Out")
    print(f"  - Total GPT-4o Cost: ${total_gpt4o_cost_usd:.2f} USD")

    print("\n" + "-"*50)
    print(f"TOTAL PIPELINE COST ESTIMATE: ${total_pipeline_cost_usd:.2f} USD")
    print(f"TOTAL PIPELINE COST ESTIMATE (INR): ₹{(total_pipeline_cost_usd * 83):.2f} INR")
    print(f"Cost per survey classification: ₹{((total_pipeline_cost_usd * 83)/num_files):.2f} INR")
    print("-"*50 + "\n")

if __name__ == "__main__":
    estimate_pipeline_cost()
