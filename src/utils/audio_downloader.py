import pandas as pd
import requests
import os
import framework_config as config

def download_audio_samples():
    print("Loading Excel file...")
    try:
        xl = pd.ExcelFile(config.EXCEL_FILE_PATH)
        df = xl.parse('Data')
    except Exception as e:
        print(f"Error loading Excel: {e}")
        return

    # Check for required columns
    if 'Audio URL' not in df.columns or 'Valid or Not' not in df.columns:
        print("Required columns 'Audio URL' or 'Valid or Not' missing.")
        return

    # Filter Valid and Invalid
    # We want ALL records for the full run
    
    # samples_to_download = df.to_dict('records')
    # Filter for random subset or full? User said "validate for all the records".
    # Let's take all.
    samples_to_download = df.to_dict('records')

    print(f"Downloading all {len(samples_to_download)} samples...")

    samples_metadata = []

    for i, record in enumerate(samples_to_download):
        url = record.get('Audio URL')
        sample_id = record.get('Sample ID', f'sample_{i}')
        validity = record.get('Valid or Not')
        
        if not isinstance(url, str) or not url.startswith('http'):
            print(f"Skipping invalid URL for sample {sample_id}")
            continue

        filename = f"{validity}_{sample_id}.mp3"
        filepath = os.path.join(config.AUDIO_DOWNLOAD_DIR, filename)

        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"Downloaded: {filename}")
                
                # Save metadata for next steps
                samples_metadata.append({
                    'file_path': filepath,
                    'url': url,
                    'sample_id': sample_id,
                    'ground_truth_validity': validity,
                    'qc_remark': record.get('QC Remark'),
                    'qc_comment': record.get('QC Comment'),
                    # Store key fields to validate against
                    'Q1': record.get('Q1: స్థానికంగా మీకున్న ప్రధానమైన సమస్యలు ఏమిటి?'),
                    'Caste': record.get('Caste'),
                    'Age': record.get('Q15: వయసు'),
                    
                })
            else:
                print(f"Failed to download {url}: Status {response.status_code}")
        except Exception as e:
            print(f"Error downloading {url}: {e}")

    # Save metadata to CSV for the next script to use
    metadata_df = pd.DataFrame(samples_metadata)
    metadata_df.to_csv(os.path.join(config.AUDIO_DOWNLOAD_DIR, 'downloaded_metadata.csv'), index=False)
    print("Download complete. Metadata saved.")

if __name__ == "__main__":
    download_audio_samples()
