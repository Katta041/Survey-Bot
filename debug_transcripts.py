import pandas as pd

DATA_PATH = "/Users/aierarohit/Desktop/Political Data/audio_samples/transcribed_metadata_sarvam.csv"
df = pd.read_csv(DATA_PATH)

keywords_to_check = [
    "MLA", "ఎమ్మెల్యే", 
    "Gollalapalli", "గొల్లపల్లి", 
    "Rapacca", "రాపాక", 
    "Performance", "పనితీరు", 
    "Bagundi", "బాగుంది", 
    "Bagoledu", "బాగోలేదు",
    "Cheyatledu", "చేయట్లేదు"
]

print(f"Total Transcripts: {len(df)}")
print("-" * 30)

for kw in keywords_to_check:
    # Check case-insensitive string match
    count = df['transcript'].str.contains(kw, case=False, na=False).sum()
    print(f"Keyword '{kw}': {count} matches")

    if count > 0 and count < 5:
        # Print a sample if few matches
        print("Sample:", df[df['transcript'].str.contains(kw, case=False, na=False)]['transcript'].iloc[0])

print("-" * 30)
