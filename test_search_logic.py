import pandas as pd

DATA_PATH = "/Users/aierarohit/Desktop/Political Data/audio_samples/transcribed_metadata_sarvam.csv"
try:
    df = pd.read_csv(DATA_PATH)
except:
    print("Could not load data")
    exit()

# ensure string
df['transcript'] = df['transcript'].astype(str)

# These are the keywords we EXPECT the LLM to generate based on the system prompt
expected_keywords = ["ఎమ్మెల్యే", "పనితీరు", "బాగుంది", "బాగోలేదు"]

print(f"Testing search with keywords: {expected_keywords}")

# Logic from survey_chatbot.py
mask = df['transcript'].str.contains('|'.join(expected_keywords), case=False, na=False)
matches = df[mask]

print(f"Total Matches Found: {len(matches)}")

if not matches.empty:
    print("Sample Match:")
    print(matches.iloc[0]['transcript'])
else:
    print("No matches found. Investigating individual keywords...")
    for kw in expected_keywords:
        c = df['transcript'].str.contains(kw, case=False, na=False).sum()
        print(f"Keyword '{kw}': {c}")
