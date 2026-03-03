import pandas as pd
import os

df_transcripts = pd.read_csv("audio_samples/tn_samples/tn_transcribed_metadata_sarvam.csv")
excel_path = "Tamil Nadu/THIRUVOTTIYUR_2026-02-19_to_2026-02-20.xlsx"
df_excel = pd.read_excel(excel_path)

cols_to_drop = ['Caste', 'Age', 'Gender', 'Q1_MLA', 'Q3_Next_CM']
for c in cols_to_drop:
    if c in df_transcripts.columns:
        df_transcripts.drop(columns=[c], inplace=True)
        
df = pd.merge(df_transcripts, df_excel, left_on='url', right_on='Audio URL', how='left')

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

print("Total rows:", len(df))
print("Next_CM unique values:")
print(df['Next_CM'].value_counts(dropna=False))
print("\nUnique Vijay mentions in Next_CM:", df['Next_CM'].str.contains('விஜய்', na=False).sum())
print("Unique Stalin mentions in Next_CM:", df['Next_CM'].str.contains('ஸ்டாலின்', na=False).sum())
