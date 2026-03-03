import pandas as pd
import json

path = "/Users/aierarohit/Desktop/Political Data/Tamil Nadu/THIRUVOTTIYUR_2026-02-19_to_2026-02-20.xlsx"
xl = pd.ExcelFile(path)
print("Sheets:", xl.sheet_names)

df = xl.parse(xl.sheet_names[0])
print(f"Shape: {df.shape}")
print("Columns:", list(df.columns))

# Let's count audio urls
audio_cols = [c for c in df.columns if 'url' in c.lower() or 'audio' in c.lower() or 'voice' in c.lower() or 'link' in c.lower()]
print("Audio columns found:", audio_cols)
if audio_cols:
    count = df[audio_cols[0]].notna().sum()
    print(f"Valid audio samples in {audio_cols[0]}: {count}")

