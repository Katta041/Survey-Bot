import pandas as pd
import openai
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Load API Key
try:
    from framework_config import OPENAI_API_KEY
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
except ImportError:
    logging.error("Error: framework_config.py not found.")
    exit(1)

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Load Data (Matched with survey_chatbot.py logic)
DATA_PATH = "/Users/aierarohit/Desktop/Political Data/audio_samples/transcribed_metadata_sarvam.csv"
try:
    df_transcripts = pd.read_csv(DATA_PATH)
    excel_path = "/Users/aierarohit/Desktop/Political Data/Razole_Overall Data_V2.xlsx"
    if os.path.exists(excel_path):
        df_excel = pd.read_excel(excel_path, sheet_name='Data')
        df = pd.merge(df_transcripts, df_excel, left_on='url', right_on='Audio URL', how='left', suffixes=('', '_excel'))
    else:
        df = df_transcripts

    column_aliases = {
        'Q10: మీరు 2024 అసెంబ్లీ ఎన్నికలో ఏ పార్టీ కి వోట్ వేశారు?': 'Vote_2024',
        'Q11: YSRCP నియోజకవర్గ  ఇంచార్జి(Gollalapalli Surya Rao) అందుబాటులో ఉంటున్నారా?': 'Incharge_Status',
        'Q12: ఒకవేళ YSRCP నియోజకవర్గ ఇంచార్జి ని మార్చాల్సి వస్తే ఎవరైతే బాగుంటుంది అని మీరు భావిస్తున్నారు? (ఈ ప్రశ్న 2024 అసెంబ్లీ ఎన్నికలో YSRCPకి ఓటు వేసినవారికి మాత్రమే చూపించబడుతుంది)': 'Incharge_Replacement'
    }
    df.rename(columns=column_aliases, inplace=True)
    
    # Ensure all object columns are strings
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str)

except Exception as e:
    logging.error(f"Data Load Error: {e}")
    exit(1)

# Mock Logic (Copied from survey_chatbot.py for fidelity)
def mock_generate_decision(user_query, lang):
    unique_castes = df['Caste'].unique().tolist() if 'Caste' in df.columns else []
    unique_problems = df['Q1'].unique().tolist() if 'Q1' in df.columns else []
    unique_votes = df['Vote_2024'].unique().tolist() if 'Vote_2024' in df.columns else []
    
    system_prompt = f"""
    You are a data analyst assistant for a political survey dataset.
    The dataset has columns: `Q1` (Problem Topic), `Caste`, `Age`, `Vote_2024`, `Incharge_Status`, `Incharge_Replacement`, `transcript`.
    
    **IMPORTANT: You must output JSON.**
    
    ### SCHEMA MAPPING (English -> Dataset Values):
    - **Caste:** {unique_castes}
      - కాపు -> 'Kapu'
      - మాల -> 'Mala'
      - శెట్టిబలిజ -> 'Settibalija'
    - **Q1 (Problems):** {unique_problems}
      - Water -> ['సాగునీరు', 'త్రాగునీరు']
      - Drainage -> ['డ్రైనేజి']
      - Roads -> ['రోడ్లు']
    - **Vote_2024:** {unique_votes}
      - YSRCP -> ['YSRCP']
      - TDP -> ['TDP']
    
    Current User Query: "{user_query}"
    Output Language: {lang}

    DECISION LOGIC:
    1. If COUNT/AGGREGATION: Return {{"type": "code", "code": "..."}}
       - The 'code' must be valid Python/Pandas code that operates on a dataframe named `df`.
       - Returns the result directly (e.g., `df['Vote_2024'].value_counts()`).
       - Use columns: `Vote_2024`, `Caste`, `Q1`.
       - **CRITICAL:** Use `.str.contains` or lists for filtering. NO SQL.
    2. If QUALITATIVE: Return {{"type": "search", "keywords": ["..."], "topic": "..."}}
       - Keywords must be Telugu terms (e.g., "నీరు", "సమస్య").
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"type": "error", "message": str(e)}

def execute_code(code, df):
    local_vars = {"df": df, "pd": pd}
    try:
        return eval(code, {}, local_vars)
    except Exception as e:
        return f"Error: {e}"

# --- SUGGESTED QUESTIONS TO TEST ---
variations = [
    # English - Quantitative
    {"q": "How many people voted for YSRCP?", "lang": "English", "type": "code"},
    {"q": "Count of people with water issues in Kapu caste", "lang": "English", "type": "code"},
    
    # English - Qualitative
    {"q": "What are the complaints about the MLA?", "lang": "English", "type": "search"},
    
    # Telugu - Quantitative (Direct Translation)
    {"q": "YSRCP కి ఓటు వేసిన వారు ఎంతమంది?", "lang": "Telugu", "type": "code"},
    {"q": "కాపు కులంలో నీటి సమస్యలు ఉన్నవారెందరు?", "lang": "Telugu", "type": "code"},
    
    # Telugu - Qualitative
    {"q": "ఎమ్మెల్యే పనితీరు పై ప్రజల అభిప్రాయం ఏమిటి?", "lang": "Telugu", "type": "search"},
    
    # Complex / Election Strategy
    {"q": "Who wants to change the Incharge?", "lang": "English", "type": "code"}, # Should use Incharge_Replacement column
]

print(f"--- TESTING {len(variations)} UI SUGGESTIONS ---\n")

for i, var in enumerate(variations):
    print(f"[{i+1}] Query ({var['lang']}): {var['q']}")
    decision = mock_generate_decision(var['q'], var['lang'])
    
    if decision['type'] != var['type']:
        print(f"❌ FAILED TYPE: Expected {var['type']}, Got {decision['type']}")
        continue

    if decision['type'] == 'code':
        print(f"   Code: {decision['code']}")
        res = execute_code(decision['code'], df)
        print(f"   Result: {res}")
        if isinstance(res, (int, float, pd.Series)) and str(res) != "0": # Basic validation
             print("   ✅ Valid Result")
        else:
             print("   ⚠️ Result is 0 or Empty (Verify if correct)")
             
    elif decision['type'] == 'search':
        print(f"   Keywords: {decision['keywords']}")
        if len(decision['keywords']) > 0:
            print("   ✅ Keywords Generated")
        else:
            print("   ❌ No Keywords")
    print("-" * 30)
