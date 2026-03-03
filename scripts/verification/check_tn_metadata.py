import os
import pandas as pd

tn_dir = "/Users/aierarohit/Desktop/Political Data/audio_samples/tn_samples"
metadata_path = os.path.join(tn_dir, "tn_downloaded_metadata.csv")

if os.path.exists(metadata_path):
    print("Found tn_downloaded_metadata.csv")
    df = pd.read_csv(metadata_path)
    print("Columns:", df.columns.tolist())
    print("\nFirst row sample:")
    if not df.empty:
        print(df.iloc[0].to_dict())
    print(f"\nTotal rows: {len(df)}")
else:
    print("tn_downloaded_metadata.csv not found. Are we sure it's downloaded?")
    
# check for transcribed files
files = os.listdir(tn_dir)
csvs = [f for f in files if f.endswith('.csv')]
print("\nCSV files in tn_samples:", csvs)
