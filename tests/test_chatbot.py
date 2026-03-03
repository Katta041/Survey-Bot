import pandas as pd
import openai
import os
import json
import sys

# Load API Key
try:
    from framework_config import OPENAI_API_KEY
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
except ImportError:
    print("Error: framework_config.py not found.")
    sys.exit(1)

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Load Data
DATA_PATH = "/Users/aierarohit/Desktop/Political Data/audio_samples/transcribed_metadata_sarvam.csv"
if not os.path.exists(DATA_PATH):
    print(f"Error: Data file not found at {DATA_PATH}")
    sys.exit(1)

df_transcripts = pd.read_csv(DATA_PATH)
print("DEBUG: Transcripts Columns:", df_transcripts.columns.tolist())

# Load Excel Data for Election Columns
excel_path = "/Users/aierarohit/Desktop/Political Data/Razole_Overall Data_V2.xlsx"
if os.path.exists(excel_path):
    try:
        df_excel = pd.read_excel(excel_path, sheet_name='Data')
        df = pd.merge(df_transcripts, df_excel, left_on='url', right_on='Audio URL', how='left', suffixes=('', '_excel'))
    except Exception as e:
        print(f"Error loading Excel data: {e}")
        df = df_transcripts # Fallback
else:
    df = df_transcripts

# Normalize column names if needed
column_aliases = {
    'Q10: మీరు 2024 అసెంబ్లీ ఎన్నికలో ఏ పార్టీ కి వోట్ వేశారు?': 'Vote_2024',
    'Q11: YSRCP నియోజకవర్గ  ఇంచార్జి(Gollalapalli Surya Rao) అందుబాటులో ఉంటున్నారా?': 'Incharge_Status',
    'Q12: ఒకవేళ YSRCP నియోజకవర్గ ఇంచార్జి ని మార్చాల్సి వస్తే ఎవరైతే బాగుంటుంది అని మీరు భావిస్తున్నారు? (ఈ ప్రశ్న 2024 అసెంబ్లీ ఎన్నికలో YSRCPకి ఓటు వేసినవారికి మాత్రమే చూపించబడుతుంది)': 'Incharge_Replacement'
}
df.rename(columns=column_aliases, inplace=True)

print("DEBUG: Columns after merge:", df.columns.tolist())
try:
    print("DEBUG: First row Caste:", df['Caste'].iloc[0])
except Exception as e:
    print(f"DEBUG Error accessing Caste: {e}")

for col in ['Q1', 'Caste', 'Age', 'transcript', 'qc_remark', 'Vote_2024', 'Incharge_Status']:
    if col in df.columns:
        df[col] = df[col].astype(str)

# Mock the chatbot logic (copied from survey_chatbot.py for testing)
def generate_decision(user_query, history=[]):
    unique_castes = df['Caste'].unique().tolist()
    unique_problems = df['Q1'].unique().tolist()
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
    
    **IMPORTANT: You must output JSON.**
    
    ### SCHEMA MAPPING (English -> Dataset Values):
    - **Caste:** {unique_castes}
    - **Q1 (Problems):** {unique_problems}
      - Water -> ['సాగునీరు', 'త్రాగునీరు']
      - Drainage -> ['డ్రైనేజి']
      - Roads -> ['రోడ్లు']
    - **Vote_2024:** {unique_votes}
      - YSRCP -> ['YSRCP']
      - TDP -> ['TDP']
      - JSP -> ['JSP']
    
    Current User Query: "{user_query}"
    Output Language: English
    Previous Context: {history[-3:] if history else "None"}

    DECISION LOGIC:
    1. If COUNT/AGGREGATION: Return {{"type": "code", "code": "..."}} (Valid Pandas code on `df`).
       - Use `.isin(['...'])` for multiple values.
    2. If QUALITATIVE: Return {{"type": "search", "keywords": ["..."], "topic": "..."}}
    3. If CHAT: Return {{"type": "chat", "response": "..."}}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def execute_code(code, df):
    local_vars = {"df": df, "pd": pd}
    try:
        return eval(code, {}, local_vars)
    except Exception as e:
        return f"Error: {e}"

# --- TEST CASES ---
tests = [
    {
        "name": "Quantitative: Kapu + Water",
        "query": "How many people in Kapu caste have water issues?",
        "history": [],
        "expected_type": "code",
        "validator": lambda res: isinstance(res, (int, pd.Series)) and str(res) != "0" # Expect non-zero if data exists
    },
    {
        "name": "Qualitative: MLA Performance",
        "query": "What are people saying about the MLA's performance?",
        "history": [],
        "expected_type": "search",
        "validator": lambda res: "keywords" in res and len(res["keywords"]) > 0
    },
    {
        "name": "Quantitative: Election - YSRCP Votes",
        "query": "How many people voted for YSRCP in 2024?",
        "history": [],
        "expected_type": "code",
        "validator": lambda res: isinstance(res, (int, pd.Series)) # Expect count
    },
    {
        "name": "Context: Any other caste?",
        "query": "Any other caste talking about water issues?",
        "history": [
            {"role": "user", "content": "How many people in Kapu caste have water issues?"},
            {"role": "assistant", "content": "There are 5 Kapu members with water issues."}
        ],
        "expected_type": "code",
        "validator": lambda res: True # Hard to validate exact logic without inspecting code, but type should be code
    }
]

print("--- RUNNING CHATBOT TESTS ---")
for test in tests:
    print(f"\nTest: {test['name']}")
    print(f"Query: {test['query']}")
    
    try:
        decision = generate_decision(test["query"], test["history"])
        print(f"Decision Type: {decision.get('type')}")
        
        if decision["type"] != test["expected_type"]:
            print(f"❌ FAILED: Expected {test['expected_type']}, got {decision['type']}")
            continue
            
        if decision["type"] == "code":
            print(f"Generated Code: {decision['code']}")
            result = execute_code(decision['code'], df)
            print(f"Execution Result: {result}")
            if test["validator"](result):
                print("✅ PASSED")
            else:
                print("❌ FAILED: Validator returned False (Result likely 0 or invalid)")
                
        elif decision["type"] == "search":
            print(f"Keywords: {decision['keywords']}")
            if test["validator"](decision):
                print("✅ PASSED")
            else:
                 print("❌ FAILED: Validator returned False")

    except Exception as e:
        print(f"❌ ERROR: {e}")

print("\n--- TESTS COMPLETE ---")
