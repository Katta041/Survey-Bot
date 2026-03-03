import pandas as pd
import os

file_path = '/Users/aierarohit/Desktop/Political Data/Razole_Overall Data_V2.xlsx'

print(f"Inspecting file: {file_path}")

try:
    # Load the Excel file to get sheet names
    xl = pd.ExcelFile(file_path)
    print(f"Sheet names: {xl.sheet_names}")

    # Look for 'data' sheet or similar
    target_sheet = None
    for sheet in xl.sheet_names:
        if 'data' in sheet.lower():
            target_sheet = sheet
            break
            
    if target_sheet:
        print(f"\n--- Inspecting Target Sheet: {target_sheet} ---")
        df = xl.parse(target_sheet)
        print(f"Shape: {df.shape}")
        print("Columns:")
        for col in df.columns:
            print(col)
            
        print("\nFirst 3 rows:")
        print(df.head(3))
        
        # Check for voice/audio columns
        voice_cols = [c for c in df.columns if 'voice' in c.lower() or 'audio' in c.lower() or 'rec' in c.lower() or 'url' in c.lower()]
        if voice_cols:
            print(f"\nPotential Voice/Audio Columns found: {voice_cols}")
            for vc in voice_cols:
                print(f"Sample values in {vc}:")
                print(df[vc].head(5))
        else:
            print("\nNo obvious voice/audio columns found based on keywords (voice, audio, rec, url).")

    else:
        print("\n'Data' sheet not found. Inspecting first sheet instead.")
        first_sheet = xl.sheet_names[0]
        df = xl.parse(first_sheet)
        print(f"Columns in {first_sheet}: {df.columns.tolist()}")

except Exception as e:
    print(f"Error inspecting Razole Excel file: {e}")
