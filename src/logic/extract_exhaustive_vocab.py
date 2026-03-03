import pandas as pd
from collections import Counter
import re

DATA_PATH = "/Users/aierarohit/Desktop/Political Data/audio_samples/transcribed_metadata_sarvam.csv"
try:
    df = pd.read_csv(DATA_PATH)
except Exception as e:
    print(f"Error loading csv: {e}")
    exit()

# Seed categories with potential Telugu/English terms
# Format: Category -> List of (English Label, [Telugu Terms to check])
categories = {
    "Infrastructure": [
        ("Roads", ["road", "rodd", "దారి", "రోడ్డు", "రోడ్లు", "guantalu", "గుంతలు"]),
        ("Water", ["water", "neeru", "నీరు", "మంచినీరు", "త్రాగునీరు", "colai", "కొళాయి"]),
        ("Drainage", ["drain", "drainage", "kalava", "కాలువ", "డ్రైనేజ్", "మురికి"]),
        ("Power/Lights", ["current", "power", "light", "veyyam", "కరెంట్", "లైటు", "స్తంభం", "velugu"]),
        ("Housing", ["house", "illu", "ఇల్లు", "colony", "కాలనీ", "sthalalu", "స్థలాలు"])
    ],
    "Schemes/Welfare": [
        ("Pension", ["pension", "pemkam", "పెన్షన్", "పింఛన్"]),
        ("Ration", ["ration", "biyyam", "రేషన్", "బియ్యం"]),
        ("Schemes (General)", ["scheme", "pathakam", "పథకం", "labbhi", "లబ్ది"]),
        ("Specific Schemes", ["ammavodi", "amma vodi", "cheyutha", "asara", "vidya deevena", "rythu", "అమ్మ ఒడి", "చేయూత", "రైతు"])
    ],
    "Governance/Officials": [
        ("Volunteer", ["volunteer", "valanteer", "వాలంటీర్"]),
        ("Secretariat", ["secretariat", "sachivalayam", "సచివాలయం", "ofisu", "ఆఫీసు"]),
        ("MLA/Leader", ["mla", "emlye", "ఎమ్మెల్యే", "nayakudu", "నాయకుడు"]),
        ("Incharge", ["incharge", "incharg", "ఇంచార్జ్"]),
        ("CM/Jagan/Babu", ["jagan", "jagananna", "cm", "babu", "chandrababu", "jagun", "జగన్", "బాబు", "పవన్"])
    ],
    "Sentiment/Action": [
        ("Good/Keep", ["good", "bagundi", "baagundi", "super", "manchiga", "వుంచాలి", "బాగుంది", "మంచి"]),
        ("Bad/Remove", ["bad", "bagoledu", "baledu", "waste", "west", "బాగోలేదు", "చెత్త", "వెస్ట్"]),
        ("Change", ["change", "marchali", "marpu", "kavali", "మార్చాలి", "వద్దు", "marpu"]),
        ("Win", ["win", "gelustaru", "gelupu", "geliche", "గెలుస్తారు", "గెలుపు"]),
        ("Lose", ["lose", "odipotaru", "odipoye", "ఓడిపోతారు"])
    ],
    "Issues/Corruption": [
        ("Money/Bribe", ["money", "dabbu", "lancham", "డబ్బు", "లంచం", "rate", "రేట్లు"]),
        ("Jobs", ["job", "udyogam", "pani", "ఉద్యోగం", "పని"])
    ]
}

print(f"--- EXHAUSTIVE VOCABULARY ANALYSIS (Total Transcripts: {len(df)}) ---\n")

def check_terms(terms):
    matches = {}
    for term in terms:
        # Case insensitive match
        count = df['transcript'].str.contains(term, case=False, na=False).sum()
        if count > 0:
            matches[term] = count
    return matches

final_glossary = {}

for cat_name, subcats in categories.items():
    print(f"[{cat_name.upper()}]")
    has_cat_matches = False
    for subcat_label, terms in subcats:
        matches = check_terms(terms)
        if matches:
            # Sort by frequency
            sorted_matches = dict(sorted(matches.items(), key=lambda item: item[1], reverse=True))
            print(f"  {subcat_label}: {sorted_matches}")
            has_cat_matches = True
            
            # Store for potential output filtering
            final_glossary[subcat_label] = list(sorted_matches.keys())
            
    if not has_cat_matches:
        print("  (No significant matches)")
    print("")

print("-" * 30)
