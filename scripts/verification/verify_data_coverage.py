import pandas as pd
import os

# Paths
EXCEL_PATH = "/Users/aierarohit/Desktop/Political Data/Razole_Overall Data_V2.xlsx"
TRANSCRIPT_PATH = "/Users/aierarohit/Desktop/Political Data/audio_samples/transcribed_metadata_sarvam.csv"

def verify_coverage():
    print("--- DATA COVERAGE AUDIT ---\n")
    
    # 1. Load Excel Source
    if not os.path.exists(EXCEL_PATH):
        print(f"❌ Excel file not found: {EXCEL_PATH}")
        return
        
    try:
        df_excel = pd.read_excel(EXCEL_PATH, sheet_name='Data')
        print(f"✅ Loaded Excel Source. Total Rows: {len(df_excel)}")
    except Exception as e:
        print(f"❌ Error loading Excel: {e}")
        return

    # 2. Load Transcripts
    if not os.path.exists(TRANSCRIPT_PATH):
        print(f"❌ Transcript file not found: {TRANSCRIPT_PATH}")
        return
        
    try:
        df_transcripts = pd.read_csv(TRANSCRIPT_PATH)
        print(f"✅ Loaded Transcripts. Total Rows: {len(df_transcripts)}")
    except Exception as e:
        print(f"❌ Error loading Transcripts: {e}")
        return

    # 3. Analyze Audio URLs
    # Clean URLs (strip whitespace, handle NaNs)
    excel_urls = df_excel['Audio URL'].dropna().astype(str).str.strip().unique()
    transcript_urls = df_transcripts['url'].dropna().astype(str).str.strip().unique()
    
    print(f"\n--- AUDIO FILE COUNTS ---")
    print(f"Unique Audio URLs in Excel: {len(excel_urls)}")
    print(f"Unique Audio URLs in Transcripts: {len(transcript_urls)}")
    
    # Intersection
    common_urls = set(excel_urls).intersection(set(transcript_urls))
    print(f"Common URLs (In both): {len(common_urls)}")
    
    # Missing
    missing_in_transcripts = set(excel_urls) - set(transcript_urls)
    missing_in_excel = set(transcript_urls) - set(excel_urls)
    
    print(f"Missing in Transcripts (Have URL but no transcript): {len(missing_in_transcripts)}")
    print(f"Extra in Transcripts (Not in Excel source?!): {len(missing_in_excel)}")
    
    if len(missing_in_transcripts) > 0:
        print("\nEnsure all 910 files were processed. If count is < 910, some batch jobs might have failed or weren't submitted.")

    # 4. Metadata Column Check
    print(f"\n--- METADATA COLUMNS (Chatbot) ---")
    # Simulate the merge done in chatbot
    df_merged = pd.merge(df_transcripts, df_excel, left_on='url', right_on='Audio URL', how='left', suffixes=('', '_excel'))
    
    print(f"Merged DataFrame Shape: {df_merged.shape}")
    print(f"Columns available to Chatbot: {len(df_merged.columns)}")
    
    # Check for critical political columns presence
    critical_cols = [
        'Q10: మీరు 2024 అసెంబ్లీ ఎన్నికలో ఏ పార్టీ కి వోట్ వేశారు?',
        'Q11: YSRCP నియోజకవర్గ  ఇంచార్జి(Gollalapalli Surya Rao) అందుబాటులో ఉంటున్నారా?',
        'Mandal Factor', 'Age', 'Caste'
    ]
    
    print("\nCritical Column Check:")
    for col in critical_cols:
        if col in df_merged.columns:
             print(f"✅ Found: {col}")
        else:
             print(f"❌ MISSING: {col}")

if __name__ == "__main__":
    verify_coverage()
