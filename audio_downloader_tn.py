import pandas as pd
import requests
import os
import framework_config as config

def download_audio_samples_tn():
    tn_excel_path = "/Users/aierarohit/Desktop/Political Data/Tamil Nadu/THIRUVOTTIYUR_2026-02-19_to_2026-02-20.xlsx"
    tn_download_dir = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'tn_samples')
    os.makedirs(tn_download_dir, exist_ok=True)
    
    print("Loading TN Excel file...")
    try:
        xl = pd.ExcelFile(tn_excel_path)
        # Using the first sheet instead of hardcoded 'Data' since it's a new file
        df = xl.parse(xl.sheet_names[0])
    except Exception as e:
        print(f"Error loading Excel: {e}")
        return

    # Check for required columns
    url_col = 'Audio URL'
    if url_col not in df.columns:
        print(f"Required column '{url_col}' missing.")
        return

    samples_to_download = df.to_dict('records')
    print(f"Downloading all {len(samples_to_download)} TN samples...")

    samples_metadata = []

    for i, record in enumerate(samples_to_download):
        url = record.get(url_col)
        sample_id = record.get('Sample ID', f'tn_sample_{i}')
        validity = record.get('QC Status', 'Unknown') # e.g., 'Done'
        
        if not isinstance(url, str) or not url.startswith('http'):
            print(f"Skipping invalid URL for sample {sample_id}")
            continue

        filename = f"{sample_id}.mp4" # or mp3
        filepath = os.path.join(tn_download_dir, filename)

        try:
            # Check if file already exists to avoid re-downloading
            if not os.path.exists(filepath):
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    print(f"Downloaded: {filename}")
                else:
                    print(f"Failed to download {url}: Status {response.status_code}")
                    continue
            else:
                pass # Already downloaded
                
            # Save metadata for next steps
            samples_metadata.append({
                'file_path': filepath,
                'url': url,
                'sample_id': sample_id,
                'qc_status': validity,
                'qc_score': record.get('QC Score'),
                'qc_comment': record.get('QC Comment'),
                'qc_remark': record.get('QC Remark'),
                # Key TN Data Fields
                'Q1_MLA': record.get('Q1: உங்கள் தொகுதி சட்டமன்ற உறுப்பினரின் (MLA) செயல்பாடுகளால் நீங்கள் திருப்தியாக உள்ளீர்களா?/ Are you satisfied with the performance of your constituency MLA?'),
                'Q3_Next_CM': record.get('Q3: தமிழ்நாட்டின் அடுத்த முதலமைச்சராக நீங்கள் யாரை ஆதரிக்கிறீர்கள்?/ Whom do you support as Tamil Nadu’s next Chief Minister?'),
                'Caste': record.get('Q13: சாதி/Caste'),
                'Age': record.get('Q10: வயது பிரிவு/Age Group'),
                'Gender': record.get('Q9: பாலினம்/Gender')
            })

        except Exception as e:
            print(f"Error downloading {url}: {e}")

    # Save metadata to CSV for the next script to use
    metadata_df = pd.DataFrame(samples_metadata)
    output_meta_path = os.path.join(tn_download_dir, 'tn_downloaded_metadata.csv')
    metadata_df.to_csv(output_meta_path, index=False)
    print(f"Download complete. Metadata saved to {output_meta_path}.")

if __name__ == "__main__":
    download_audio_samples_tn()
