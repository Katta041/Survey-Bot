import pandas as pd
from collections import Counter
import re

DATA_PATH = "/Users/aierarohit/Desktop/Political Data/audio_samples/transcribed_metadata_sarvam.csv"
df = pd.read_csv(DATA_PATH)

# Common political concepts we want to map
concepts = {
    "Roads": ["road", "rodd", "దారి", "రోడ్డు", "రోడ్లు"],
    "Water": ["water", "neeru", "నీరు", "మంచినీరు", "త్రాగునీరు"],
    "Money/Bribe": ["money", "dabbu", "డబ్బు", "లంచం", "డబ్బులు"],
    "Schemes/Welfare": ["scheme", "pathakam", "పథకం", "పెన్షన్", "ఇల్లు"],
    "Good": ["good", "bagundi", "baagundi", "బాగుంది", "మంచి"],
    "Bad": ["bad", "bagoledu", "baledu", "బాగోలేదు", "చెత్త"],
    "MLA": ["mla", "emlye", "ఎమ్మెల్యే", "నాయకుడు"],
    "Change": ["change", "marchali", "మార్చాలి", "వద్దు"],
}

print(f"--- VOCABULARY FREQUENCY ANALYSIS (Total: {len(df)}) ---\n")

for category, terms in concepts.items():
    print(f"[{category}]")
    found_any = False
    for term in terms:
        # Simple substring match count
        count = df['transcript'].str.contains(term, case=False, na=False).sum()
        if count > 0:
            print(f"  - '{term}': {count} occurrences")
            found_any = True
            
    if not found_any:
        print("  (No matches found for common terms)")
    print("")

print("-" * 30)
