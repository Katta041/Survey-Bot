import pandas as pd
import os

print("Creating Anonymized Dataset for TN Chatbot...")

# 1. Load Transcripts
transcript_path = "/Users/aierarohit/Desktop/Political Data/audio_samples/tn_samples/tn_transcribed_metadata_sarvam.csv"
df_transcripts = pd.read_csv(transcript_path)

# Drop any previous PII or overlapping columns from transcripts
cols_to_drop = ['Caste', 'Age', 'Gender', 'Q1_MLA', 'Q3_Next_CM']
for c in cols_to_drop:
    if c in df_transcripts.columns:
        df_transcripts.drop(columns=[c], inplace=True)

# 2. Load Excel
excel_path = "/Users/aierarohit/Desktop/Political Data/Tamil Nadu/THIRUVOTTIYUR_2026-02-19_to_2026-02-20.xlsx"
df_excel = pd.read_excel(excel_path)
for c in ['Gender', 'Caste']:
    if c in df_excel.columns:
        df_excel.drop(columns=[c], inplace=True)

# 3. Merge
df = pd.merge(df_transcripts, df_excel, left_on='url', right_on='Audio URL', how='left')

# 4. Rename Columns to Aliases (same as chatbot logic)
column_aliases = {
    'Q1: உங்கள் தொகுதி சட்டமன்ற உறுப்பினரின் (MLA) செயல்பாடுகளால் நீங்கள் திருப்தியாக உள்ளீர்களா?/ Are you satisfied with the performance of your constituency MLA?': 'MLA_Satisfaction',
    'Q2: வரவிருக்கும் சட்டமன்ற தேர்தலில் ஆட்சி மாற்றம் தேவையென நீங்கள் நினைக்கிறீர்களா?/ Do you feel a change in government is needed in the coming assembly Elections?': 'Desires_Change',
    'Q3: தமிழ்நாட்டின் அடுத்த முதலமைச்சராக நீங்கள் யாரை ஆதரிக்கிறீர்கள்?/ Whom do you support as Tamil Nadu’s next Chief Minister?': 'Next_CM',
    'Q4: வரவிருக்கும் சட்டமன்ற தேர்தலில் நீங்கள் எந்தக் கட்சி / கூட்டணிக்கு வாக்களிக்க உள்ளீர்கள்?/ Which party/ alliance will you vote in the upcoming assembly elections?': 'Vote_2026',
    'Q8: முந்தைய (2021) சட்டமன்ற தேர்தலில் நீங்கள் எந்தக் கட்சி / கூட்டணிக்கு வாக்களித்தீர்கள்?/ Which party did you vote in the previous(2021) assembly election?': 'Vote_2021',
    'Q13: சாதி/Caste': 'Caste',
    'Q9: பாலினம்/Gender': 'Gender',
    'Q10: வயது பிரிவு/Age Group': 'Age_Group'
}
df.rename(columns=column_aliases, inplace=True)

# 5. Drop Sensitive Information (PII)
sensitive_cols = [
    'Q11: பெயர்/Name', 
    'Q12: கைபேசி எண்/Mobile Number', 
    'Surveyor', 
    'QC Reviewer', 
    'QC Reviewed At',
    'QC Remark',
    'Company'
]
for col in sensitive_cols:
    if col in df.columns:
        df.drop(columns=[col], inplace=True)

# Format to Strings
columns_to_str = ['MLA_Satisfaction', 'Desires_Change', 'Next_CM', 'Vote_2026', 'Vote_2021', 'Caste', 'Gender', 'Age_Group', 'transcript', 'QC Comment']
for col in columns_to_str:
    if col in df.columns:
        df[col] = df[col].astype(str)

df = df.loc[:, ~df.columns.duplicated()]

if 'sample_id' not in df.columns:
    df['sample_id'] = df.index.astype(str)

# 6. Save
output_path = "/Users/aierarohit/Desktop/Political Data/tn_app_data_anonymized.csv"
df.to_csv(output_path, index=False)
print(f"✅ Anonymized dataset saved to: {output_path} with {len(df)} rows.")
