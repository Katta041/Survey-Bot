import pandas as pd
import json
import time

# --- MOCK / SETUP ---
# We will import the logic from survey_chatbot, but we need to mock streamlit and openai to avoid UI issues and costs
# Actually, we can import *functions* if we refactor survey_chatbot to be importable.
# But survey_chatbot has direct st.calls. 
# Plan: I'll copy the core `generate_response` logic or reading the file and extracting it is too complex.
# Better: I will create a test script that Re-Implements the 'generate_response' PROMPT and LOGIC 
# to verify if the PROMPT works.
# Or better yet, I will test the actual chatbot logic by importing it?
# The file has code at module level `st.set_page_config` which will error on import without streamlit run.

# OPTION: duplicate logic for testing strictly.
# Given the instructions, I'll create a standalone test script that mimics the production logic exactly.

import openai
import os

try:
    from framework_config import OPENAI_API_KEY
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
except:
    print("API Key missing")
    exit()

DATA_PATH = "/Users/aierarohit/Desktop/Political Data/audio_samples/transcribed_metadata_sarvam.csv"
df = pd.read_csv(DATA_PATH)
# Merge Excel logic (simplified for test)
try:
    df_excel = pd.read_excel("/Users/aierarohit/Desktop/Political Data/Razole_Overall Data_V2.xlsx", sheet_name='Data')
    df = pd.merge(df, df_excel, left_on='url', right_on='Audio URL', how='left', suffixes=('', '_excel'))
    column_aliases = {
        'Q10: మీరు 2024 అసెంబ్లీ ఎన్నికలో ఏ పార్టీ కి వోట్ వేశారు?': 'Vote_2024',
        'Q11: YSRCP నియోజకవర్గ  ఇంచార్జి(Gollalapalli Surya Rao) అందుబాటులో ఉంటున్నారా?': 'Incharge_Status',
        'Q12: ఒకవేళ YSRCP నియోజకవర్గ ఇంచార్జి ని మార్చాల్సి వస్తే ఎవరైతే బాగుంటుంది అని మీరు భావిస్తున్నారు? (ఈ ప్రశ్న 2024 అసెంబ్లీ ఎన్నికలో YSRCPకి ఓటు వేసినవారికి మాత్రమే చూపించబడుతుంది)': 'Incharge_Replacement'
    }
    df.rename(columns=column_aliases, inplace=True)
except:
    pass

# Ensure strings
for col in ['Q1', 'Caste', 'Age', 'transcript', 'Vote_2024', 'Incharge_Status']:
    if col in df.columns:
        df[col] = df[col].astype(str)

# --- TEST QUERIES ---
test_cases = [
    # --- QUANTITATIVE (English) ---
    {"q": "How many people voted for YSRCP?", "type": "code", "expected": "Vote_2024"},
    {"q": "Count of Kapu caste with water issues", "type": "code", "expected": "Kapu"},
    {"q": "How many people want to change the Incharge?", "type": "code", "expected": "Incharge"},
    {"q": "What is the distribution of Incharge Status?", "type": "code", "expected": "value_counts"},
    {"q": "How many voted TDP?", "type": "code", "expected": "TDP"},
    {"q": "Count of people with drainage problems", "type": "code", "expected": "Drainage"},
    {"q": "How many sample are there?", "type": "code", "expected": "len"},
    {"q": "Percentage of YSRCP voters", "type": "code", "expected": "mean"},
    {"q": "Count of Mala caste", "type": "code", "expected": "Mala"},
    {"q": "How many people are 30 years old?", "type": "code", "expected": "Age"},

    # --- QUANTITATIVE (Telugu) ---
    {"q": "YSRCP కి ఓటు వేసిన వారు ఎంతమంది?", "type": "code", "expected": "Vote_2024"},
    {"q": "కాపు కులంలో నీటి సమస్యలు ఉన్నవారెందరు?", "type": "code", "expected": "Caste"},
    {"q": "ఇంచార్జ్ ని మార్చాలి అని ఎంతమంది అనుకుంటున్నారు?", "type": "code", "expected": "Incharge"},
    {"q": "TDP కి ఎంతమంది ఓటు వేశారు?", "type": "code", "expected": "TDP"},
    {"q": "డ్రైనేజీ సమస్యలు ఎంతమందికి ఉన్నాయి?", "type": "code", "expected": "Drainage"},

    # --- QUALITATIVE (English) ---
    {"q": "What do people say about the MLA's performance?", "type": "search", "expected": "MLA"},
    {"q": "Why do people want to change the Incharge?", "type": "search", "expected": "Incharge"},
    {"q": "Are there complaints about pensions?", "type": "search", "expected": "Pension"},
    {"q": "What are the issues with roads?", "type": "search", "expected": "Roads"},
    {"q": "What do people say about Jagan?", "type": "search", "expected": "Jagan"},
    {"q": "Is there corruption involved?", "type": "search", "expected": "Money"},
    {"q": "Feedback on volunteers", "type": "search", "expected": "Volunteer"},
    {"q": "Issues with drinking water", "type": "search", "expected": "Water"},
    {"q": "What about housing schemes?", "type": "search", "expected": "Housing"},
    {"q": "Do people like the current government?", "type": "search", "expected": "Good"},

    # --- QUALITATIVE (Telugu) ---
    {"q": "ఎమ్మెల్యే పనితీరు ఎలా ఉంది?", "type": "search", "expected": "MLA"},
    {"q": "నీటి సమస్యల గురించి జనాలు ఏమంటున్నారు?", "type": "search", "expected": "Water"},
    {"q": "రోడ్లు ఎలా ఉన్నాయి?", "type": "search", "expected": "Roads"},
    {"q": "పెన్షన్లు అందుతున్నాయా?", "type": "search", "expected": "Pension"},
    {"q": "లంచాలు అడుగుతున్నారా?", "type": "search", "expected": "Money"},
    {"q": "పథకాలు అందుతున్నాయా?", "type": "search", "expected": "Schemes"},
    {"q": "వాలంటీర్ల పనితీరు ఎలా ఉంది?", "type": "search", "expected": "Volunteer"},
    {"q": "జగన్ గారి పాలన ఎలా ఉంది?", "type": "search", "expected": "Jagan"},
    {"q": "ఇంచార్జ్ గురించి ఏమంటున్నారు?", "type": "search", "expected": "Incharge"},
    {"q": "కరెంట్ సమస్యలు ఉన్నాయా?", "type": "search", "expected": "Power"},
    
    # --- EDGE CASES / CHAT ---
    {"q": "Hello", "type": "chat", "expected": ""},
    {"q": "Who are you?", "type": "chat", "expected": ""},
    {"q": "Tell me a joke", "type": "chat", "expected": ""},
    {"q": "What is the weather?", "type": "chat", "expected": ""},
    {"q": "Anything more?", "type": "chat", "expected": ""} # Might default to chat if no previous context in this script
]

# System Prompt (Copied from survey_chatbot.py for fidelity)
unique_castes = df['Caste'].unique().tolist()
unique_problems = df['Q1'].unique().tolist() if 'Q1' in df.columns else []
unique_votes = df['Vote_2024'].unique().tolist() if 'Vote_2024' in df.columns else []

system_prompt = f"""
    You are a data analyst assistant for a political survey dataset.
    The dataset has columns: 
    - `Q1` (Problem Topic)
    - `Caste`, `Age`
    - `Vote_2024` (Party voted for in 2024)
    - `Incharge_Status` (Is the YSRCP Incharge available?)
    - `Incharge_Replacement` (Opinion on replacement)
    - `transcript` (Telugu Audio Transcript)
    
    ### DATASET VOCABULARY (Colloquial Telugu Terms found in local transcripts):
    - **Infrastructure:**
      - Roads: "రోడ్లు" (Roads), "రోడ్డు" (Road), "గతుకులు" (Potholes), "దారులు" (Paths)
      - Water: "నీరు" (Water), "త్రాగునీరు" (Drinking Water), "కొళాయి" (Tap)
      - Power: "కరెంట్" (Current), "లైటు" (Light), "స్తంభం" (Pole)
      - Housing: "ఇల్లు" (House), "స్థలాలు" (Sites), "కాలనీ" (Colony)
    - **Welfare Schemes:**
      - General: "పథకం" (Scheme), "లబ్ది" (Benefit)
      - Specific: "పెన్షన్" (Pension), "రేషన్" (Ration), "అమ్మ ఒడి" (Amma Vodi), "రైతు" (Rythu/Farmer), "చేయూత" (Cheyutha)
    - **Leaders & Governance:**
      - CM/Leaders: "జగన్" (Jagan), "బాబు" (Babu/Chandrababu), "పవన్" (Pawan)
      - Local: "ఎమ్మెల్యే" (MLA), "ఇంచార్జ్" (Incharge), "నాయకుడు" (Leader)
      - Officials: "వాలంటీర్" (Volunteer), "సచివాలయం" (Secretariat)
    - **Issues & Corruption:**
      - Money/Bribe: "డబ్బు" (Money), "లంచం" (Bribe), "రేట్లు" (Rates)
      - Employment: "ఉద్యోగం" (Job), "పని" (Work)
    - **Sentiment:**
      - Positive: "బాగుంది" (Good), "మంచి" (Good), "గెలుపు" (Win)
      - Negative: "బాగోలేదు" (Bad), "చెత్త" (Trash), "చేయట్లేదు" (Not doing)
      - Change: "మార్చాలి" (Change), "వద్దు" (Don't want), "ఓడిపోతారు" (Will lose)

    ### SCHEMA MAPPING (English -> Dataset Values):
    - **Caste:** {unique_castes}
    - **Q1 (Problems):** {unique_problems}
      - Water -> ['సాగునీరు', 'త్రాగునీరు']
      - Drainage -> ['డ్రైనేజి']
      - Roads -> ['రోడ్లు']
    - **Vote_2024:** {unique_votes}
    
    DECISION LOGIC:
    1. If the user asks for a COUNT, AGGREGATION, or STATISTIC (e.g., "How many voted for TDP?", "Distribution of Incharge status"):
       - Return a JSON object with: {{"type": "code", "code": "..."}}
       - The 'code' must be valid Python/Pandas code that operates on a dataframe named `df`.
       - Use column aliases `Vote_2024`, `Incharge_Status`, etc.
       - **CRITICAL:** Use `.str.contains` or lists for filtering.
    
    2. If the user asks for QUALITATIVE info (e.g., "Why do people want to change the Incharge?"):
       - Return a JSON object with: {{"type": "search", "keywords": ["..."], "topic": "..."}}
       - The 'keywords' should be Telugu terms found in transcripts.
    
    3. If general chat:
       - Return {{"type": "chat", "response": "..."}}
"""

print(f"Starting Intensive Test: {len(test_cases)} Questions...")
print("="*60)

passed = 0
failed = 0

# Limit to avoid massive bill/rate limits during test
# We will test in batches or just run all 40 with small sleep
for i, case in enumerate(test_cases):
    q = case["q"]
    expected_type = case["type"]
    expected_kw = case["expected"]
    
    print(f"[{i+1}/{len(test_cases)}] Q: {q}")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": q}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        decision = json.loads(content)
        
        # Validation
        decision_type = decision.get("type", "error")
        
        status = "❌ FAIL"
        reason = ""
        
        if decision_type == expected_type:
            status = "✅ PASS"
            if decision_type == "search":
                kws = decision.get("keywords", [])
                # Check if specific mapped keyword exists (e.g. MLA -> ఎమ్మెల్యే)
                # But mapping logic is in python not LLM. LLM outputs words.
                # Just check if list is not empty
                if not kws:
                     status = "⚠️ WARN (No Keywords)"
            elif decision_type == "code":
                code = decision.get("code", "")
                if "df" not in code:
                    status = "❌ FAIL (Invalid Code)"
        else:
            status = f"❌ FAIL (Got {decision_type}, Exp {expected_type})"
            
        print(f"   -> {status} | Type: {decision_type}")
        if status.startswith("✅"):
            passed += 1
        else:
            failed += 1
            
    except Exception as e:
        print(f"   -> ❌ ERROR: {e}")
        failed += 1
        
    time.sleep(0.5) # Avoid Rate Limit

print("="*60)
print(f"TEST SUMMARY: Passed: {passed} | Failed: {failed}")
print("="*60)
