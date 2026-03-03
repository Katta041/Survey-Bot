import pandas as pd
import os
from pathlib import Path
import sys

# Add project root to path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from src.core.config import Config

def sanitize():
    print("🚀 Starting Data Sanitization...")
    
    # Paths
    transcript_path = Config.AUDIO_DIR / "tn_samples/tn_transcribed_metadata_sarvam.csv"
    excel_path = Config.RAW_DATA_DIR / "Tamil Nadu/THIRUVOTTIYUR_2026-02-19_to_2026-02-20.xlsx"
    output_dir = Config.BASE_DIR / "data/production"
    output_file = output_dir / "tn_survey_sanitized.csv"
    
    os.makedirs(output_dir, exist_ok=True)
    
    if not transcript_path.exists():
        print(f"❌ Transcription file not found: {transcript_path}")
        return
    if not excel_path.exists():
        print(f"❌ Excel file not found: {excel_path}")
        return
        
    # Load Data
    print("📖 Loading Transcription Data...")
    df_transcripts = pd.read_csv(transcript_path)
    
    print("📖 Loading Excel Data (this may take a moment)...")
    df_excel = pd.read_excel(excel_path)
    
    # Define Column Mappings (Excel to Internal)
    mapping = {
        'Audio URL': 'url',
        'Q1: உங்கள் தொகுதி சட்டமன்ற உறுப்பினரின் (MLA) செயல்பாடுகளால் நீங்கள் திருப்தியாக உள்ளீர்களா?/ Are you satisfied with the performance of your constituency MLA?': 'MLA_Satisfaction',
        'Q2: வரவிருக்கும் சட்டமன்ற தேர்தலில் ஆட்சி மாற்றம் தேவையென நீங்கள் நினைக்கிறீர்களா?/ Do you feel a change in government is needed in the coming assembly Elections?': 'Desires_Change',
        'Q3: தமிழ்நாட்டின் அடுத்த முதலமைச்சராக நீங்கள் யாரை ஆதரிக்கிறீர்கள்?/ Whom do you support as Tamil Nadu’s next Chief Minister?': 'Next_CM',
        'Q4: வரவிருக்கும் சட்டமன்ற தேர்தலில் நீங்கள் எந்தக் கட்சி / கூட்டணிக்கு வாக்களிக்க உள்ளீர்கள்?/ Which party/ alliance will you vote in the upcoming assembly elections?': 'Vote_2026',
        'Q9: பாலினம்/Gender': 'Gender_Excel',
        'Q10: வயது பிரிவு/Age Group': 'Age_Group',
        'Q13: சாதி/Caste': 'Caste_Excel',
        'Q14: தொழில்/Occupation': 'Occupation'
    }
    
    # Select only safe columns from Excel
    df_excel_safe = df_excel[list(mapping.keys())].rename(columns=mapping)
    
    # Merge
    print("🔗 Merging Datasets...")
    df_final = pd.merge(
        df_transcripts, 
        df_excel_safe, 
        on='url', 
        how='left'
    )
    
    # Cleanup: Consolidate Gender and Caste if duplicated
    if 'Gender' in df_final.columns and 'Gender_Excel' in df_final.columns:
        df_final['Gender'] = df_final['Gender'].fillna(df_final['Gender_Excel'])
        df_final.drop(columns=['Gender_Excel'], inplace=True)
    
    if 'Caste' in df_final.columns and 'Caste_Excel' in df_final.columns:
        df_final['Caste'] = df_final['Caste'].fillna(df_final['Caste_Excel'])
        df_final.drop(columns=['Caste_Excel'], inplace=True)
        
    if 'Age' in df_final.columns and 'Age_Group' in df_final.columns:
        df_final['Age_Group'] = df_final['Age_Group'].fillna(df_final['Age'])
        df_final.drop(columns=['Age'], inplace=True)

    # Final Column Check for Engine Compatibility
    # Engine expects: MLA_Satisfaction, Desires_Change, Next_CM, Vote_2026, Caste, Age_Group, Gender, transcript
    
    # Drop PII/Internal paths if they leaked
    cols_to_keep = [
        'sample_id', 'url', 'transcript', 'qc_status', 'qc_score', 'qc_comment',
        'MLA_Satisfaction', 'Desires_Change', 'Next_CM', 'Vote_2026',
        'Caste', 'Age_Group', 'Gender', 'Occupation'
    ]
    
    df_final = df_final[[c for c in cols_to_keep if c in df_final.columns]]
    
    # Save
    print(f"💾 Saving sanitized data to {output_file} ({len(df_final)} rows)...")
    df_final.to_csv(output_file, index=False)
    print("✅ Done!")

if __name__ == "__main__":
    sanitize()
