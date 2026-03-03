import pandas as pd
import json
import time
import openai
import os

try:
    from framework_config import OPENAI_API_KEY
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
except:
    print("API Key missing")
    exit()

# System Prompt (Copied from survey_chatbot.py for fidelity)
# In production, we would import this string.
system_prompt = """
    You are a data analyst assistant for a political survey dataset.
    
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
    
    DECISION LOGIC:
    1. If the user asks for a COUNT, AGGREGATION, or STATISTIC (e.g., "How many voted for TDP?", "Distribution of Incharge status"):
       - Return a JSON object with: {"type": "code", "code": "..."}
       - The 'code' must be valid Python/Pandas code that operates on a dataframe named `df`.
       - Use column aliases `Vote_2024`, `Incharge_Status`, etc.
       - **CRITICAL:** Use `.str.contains` or lists for filtering.
    
    2. If the user asks for QUALITATIVE info (e.g., "Why do people want to change the Incharge?"):
       - Return a JSON object with: {"type": "search", "keywords": ["..."], "topic": "..."}
       - The 'keywords' should be Telugu terms found in transcripts.
       
    3. If the user asks for MORE info on the previous topic (e.g., "Anything else?", "More examples"):
       - Return a JSON object with: {"type": "more_results"}
    
    3. If general chat:
       - Return {"type": "chat", "response": "..."}
"""

def test_query(q, expected_type, expected_keywords=None):
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
        
        dtype = decision.get("type")
        
        if dtype != expected_type:
            return False, f"Type mismatch: Got {dtype}, Expected {expected_type}"
            
        if dtype == "search" and expected_keywords:
            raw_keywords = decision.get("keywords", [])
            # In production key mapping happens AFTER LLM, but LLM should ideally output Telugu.
            # We strictly check if ANY of the expected terms are present
            found = False
            for ek in expected_keywords:
                for rk in raw_keywords:
                    if ek in rk:
                        found = True
                        break
            if not found:
                 return False, f"Keywords missing. Got {raw_keywords}, Expected one of {expected_keywords}"
                 
        return True, "OK"
    except Exception as e:
        return False, str(e)

print("--- PRODUCTION GRADE ASSERTIONS ---")

assertions = [
    # Verify VOCABULARY Injection worked (LLM outputs Telugu terms DIRECTLY)
    ("What about pensions?", "search", ["పెన్షన్"]), 
    ("Issues with roads", "search", ["రోడ్లు", "రోడ్డు"]),
    ("MLA Performance", "search", ["ఎమ్మెల్యే", "పనితీరు", "బాగుంది", "బాగోలేదు"]), # Strict check
    ("Money corruption", "search", ["డబ్బు", "లంచం"]),
    # Verify Pagination Trigger
    ("Give me more details", "more_results", []),
    ("Anything else?", "more_results", [])
]

passed = 0
for q, et, ek in assertions:
    print(f"Testing: '{q}' -> Expect {et} with keywords {ek}...")
    ok, msg = test_query(q, et, ek)
    if ok:
        print("   ✅ PASS")
        passed += 1
    else:
        print(f"   ❌ FAIL: {msg}")
    time.sleep(0.5)

print(f"Result: {passed}/{len(assertions)}")
