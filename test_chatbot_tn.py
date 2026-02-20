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

# --- Data Loading (TN Specific) ---
DATA_PATH = "/Users/aierarohit/Desktop/Political Data/audio_samples/tn_samples/tn_transcribed_metadata_sarvam.csv"
if not os.path.exists(DATA_PATH):
    print(f"Error: Data file not found at {DATA_PATH}")
    sys.exit(1)

df_transcripts = pd.read_csv(DATA_PATH)
cols_to_drop = ['Caste', 'Age', 'Gender', 'Q1_MLA', 'Q3_Next_CM']
for c in cols_to_drop:
    if c in df_transcripts.columns:
        df_transcripts.drop(columns=[c], inplace=True)

excel_path = "/Users/aierarohit/Desktop/Political Data/Tamil Nadu/THIRUVOTTIYUR_2026-02-19_to_2026-02-20.xlsx"
df_excel = pd.read_excel(excel_path)
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

for col in ['MLA_Satisfaction', 'Desires_Change', 'Next_CM', 'Vote_2026', 'Vote_2021', 'Caste', 'Gender', 'Age_Group', 'transcript', 'QC Comment']:
    if col in df.columns:
        df[col] = df[col].astype(str)
df = df.loc[:, ~df.columns.duplicated()]

unique_castes = df['Caste'].unique().tolist() if 'Caste' in df.columns else []
unique_next_cm = df['Next_CM'].unique().tolist() if 'Next_CM' in df.columns else []
unique_vote = df['Vote_2026'].unique().tolist() if 'Vote_2026' in df.columns else []

# --- System Prompt Definition ---
def generate_decision(user_query, history=[]):
    system_prompt = f"""
    You are a data analyst assistant for a political survey dataset in Tamil Nadu.
    The dataset has columns: 
    - `MLA_Satisfaction` (Are you satisfied with the MLA?)
    - `Desires_Change` (Do you feel a change in govt is needed?)
    - `Next_CM` (Whom do you support as next CM?)
    - `Vote_2026` (Which party will you vote for?)
    - `Caste`, `Age_Group`, `Gender`
    - `QC Comment`
    - `transcript` (Tamil Audio Transcript)
    
    ### SCHEMA MAPPING:
    - **Caste:** {unique_castes}
    - **Next_CM:** {unique_next_cm}
    - **Vote_2026:** {unique_vote}
    
    Current User Query: "{user_query}"
    Output Language: English
    Previous Context: {history[-3:] if history else "None"}

    DECISION LOGIC:
    1. If the user asks for a COUNT, AGGREGATION, or STATISTIC (e.g., "How many voted for TVK?", "Distribution of next CM"):
       - Return a JSON object with: {{"type": "code", "code": "..."}}
       - The 'code' must be valid Python/Pandas code that operates on a dataframe named `df`.
       - Use column aliases `Next_CM`, `Vote_2026`, etc.
       - **CRITICAL:** Use `.str.contains` or lists for filtering. Because columns contain Tamil/English mixed like 'விஜய் (தமிழகம் வெற்றி கழகம்)/ Vijay (TVK)', exact equals (`==`) WILL FAIL. Use `.str.contains('Vijay')` or `.str.contains('விஜய்')`.
       - **CRITICAL:** If using multiple lines of code, you MUST assign the final answer to a variable named `result`! Example: `result = {{"Vijay": vijay_count, "Stalin": stalin_count}}`
       - **CRITICAL DEFENSIVE PROGRAMMING:** The dataset is highly categorical and some combinations (like "Vanniyar") might have ZERO rows. Therefore, if you use `.idxmax()`, you MUST check if the filtered series is empty first OR wrap it in a try-except. Example: `result = counts.idxmax() if not counts.empty else "No matching data"`
       - Provide zero instead of causing `KeyError`. Replace `.shape[0]` or `.sum()` with `0` if empty.
       - **CRITICAL STRING TYPES:** ALL columns are strings, even `MLA_Satisfaction` (Yes/No). You cannot use boolean filtering like `df[df['MLA_Satisfaction']]`. You MUST use `df[df['MLA_Satisfaction'] == 'Yes']`.
       - **CRITICAL SYNTAX:** Never write invalid python syntax. Specifically, do not write malformed dictionary comprehensions. If you need to clean dictionaries, use a simple `for` loop before assigning to `result`.
    
    2. If the user asks for QUALITATIVE info (e.g., "Why do people want to change the MLA?"):
       - Return a JSON object with: {{"type": "search", "keywords": ["..."], "topic": "..."}}
       - The 'keywords' should be Tamil terms.
    
    3. If the user asks for MORE info on the previous topic:
       - Return a JSON object with: {{"type": "more_results"}}
    
    4. If general chat or follow-up:
       - Return {{"type": "chat", "response": "..."}}
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

def execute_pandas_code(code, df):
    try:
        local_vars = {"df": df, "pd": pd}
        try:
            result = eval(code, {}, local_vars)
            return result
        except SyntaxError:
            exec(code, {}, local_vars)
            if 'result' in local_vars:
                return local_vars['result']
            result = None
            for key, val in reversed(list(local_vars.items())):
                if key not in ['df', 'pd'] and not isinstance(val, type(pd)):
                    result = val
                    break
            return result
    except Exception as e:
        return f"Error executing code: {e}"

# --- TEST CASES (40 Questions) ---
# Mixing simple aggregation, complex aggregation, and qualitative search
questions = [
    # 1-10: Simple Quantitative
    "How many absolute voters we have in the dataset?",
    "How many people support Vijay for Next CM?",
    "How many people support Stalin vs Vijay?",
    "Count of people who want a change in government.",
    "How many women are in the dataset?",
    "What is the total number of people from the Vanniyar caste?",
    "How many people voted for DMK alliance in 2021?",
    "What is the distribution of Next_CM preferences?",
    "How many people are dissatisfied with the MLA?",
    "Count voters older than 50.",
    
    # 11-20: Complex / Cross-tabulation Quantitative
    "How many women support Vijay for CM?",
    "Among Vanniyars, who is the most preferred Next CM?",
    "How many people who voted for DMK in 2021 now want a change in government?",
    "Of those satisfied with the MLA, how many support Stalin?",
    "What is the most popular party for the upcoming 2026 election among Youth (18-30)?",
    "How many people who want to vote for TVK in 2026 voted for ADMK in 2021?",
    "Distribution of Next CM preference broken down by Gender.",
    "Give me the count of dissatisfied MLA voters broken down by Caste.",
    "How many people from 'Others' caste support Seeman?",
    "How many people do NOT want a change in government but support Vijay?",
    
    # 21-30: Qualitative Searches
    "What are people saying about the current MLA's performance?",
    "Why do people want Vijay as the next CM?",
    "Any complaints regarding drinking water?",
    "What are the main issues raised by women voters?",
    "Are there mentions of corruption or bribes?",
    "What do people say about the DMK alliance?",
    "Are people happy with Stalin's governance?",
    "Any comments on rural roads and infrastructure?",
    "What do people think about Seeman's speeches?",
    "Are people mentioning any specific welfare schemes?",
    
    # 31-40: Edge Cases & Conversational
    "Who is the current President of the United States?", # Should trigger chat
    "Add 234 and 567.", # Should trigger chat
    "I want more examples.", # Should trigger more_results
    "How many people support Batman for CM?", # Should run code, return 0
    "Provide a detailed breakdown of MLA satisfaction vs Desires Change.", # Code
    "Tell me a joke about politics.", # Chat
    "How many people in the dataset belong to the 'Alien' caste?", # Code -> 0
    "What do people say about alien invasions?", # Search -> empty
    "Which age group is the largest?", # Code
    "Count of people who support Stalin, Vijay, and Edappadi.", # Code
    
    # 41-45: Audio/Transcript specific questions (as requested by user)
    "How many records do we have audio URLs for?", # Code
    "Are there any blank or missing transcripts?", # Code
    "What is the longest audio transcript we have by character count?", # Code
    "How many records failed the audio QC check?", # Code
    "Which URLs correspond to people who want Seeman as CM?", # Code
    
    # 46-61: UI Suggested Questions (English & Tamil)
    "Are people satisfied with the MLA's performance?",
    "எம்.எல்.ஏ வின் செயல்பாடுகளில் மக்கள் திருப்தி அடைந்துள்ளார்களா?",
    "Who do people support as the next Chief Minister?",
    "அடுத்த முதலமைச்சராக மக்கள் யாரை ஆதரிக்கிறார்கள்?",
    "Why do people want a change in government?",
    "மக்கள் ஏன் ஆட்சி மாற்றத்தை விரும்புகிறார்கள்?",
    "What did people say about Vijay (TVK)?",
    "விஜய் (த.வெ.க) பற்றி மக்கள் என்ன சொல்கிறார்கள்?",
    "What are the main issues faced by women (Female voters)?",
    "பெண்கள் எதிர்கொள்ளும் முக்கிய பிரச்சனைகள் என்ன?",
    "How many voters support DMK alliance?",
    "திமுக கூட்டணிக்கு எவ்வளவு பேர் ஆதரவு அளிக்கின்றனர்?",
    "Summarize the sentiment towards the current CM.",
    "தற்போதைய முதல்வரைப் பற்றிய மக்களின் கருத்தை சுருக்கமாகக் கூறவும்.",
    "Who is considered the most accessible leader?",
    "மக்கள் எளிதாக அணுகக்கூடிய தலைவராக யார் கருதப்படுகிறார்?"
]

print(f"--- STARTING STRESS TEST on TN DATA ({len(df)} rows) ---")
passed = 0
failed = 0

for i, q in enumerate(questions):
    print(f"\n[Test {i+1}] Query: {q}")
    history = []
    if q == "I want more examples.":
        history = [{"role": "user", "content": "What are people saying about the current MLA's performance?"}, {"role": "assistant", "content": "People are saying it's bad."}]
        
    try:
        decision = generate_decision(q, history)
        dtype = decision.get("type")
        print(f"  -> Type Classified: {dtype}")
        
        if dtype == "code":
            code = decision.get("code", "")
            print(f"  -> Code generated:\n{code}")
            result = execute_pandas_code(code, df)
            
            if "Error executing code" in str(result):
                print(f"  ❌ FAILED: Exception in code execution -> {result}")
                failed += 1
            else:
                print(f"  ✅ PASSED: Result -> {result}")
                passed += 1
                
        elif dtype == "search":
            print(f"  ✅ PASSED: Search keywords -> {decision.get('keywords')}")
            passed += 1
        elif dtype == "chat":
            print(f"  ✅ PASSED: Chat response -> {decision.get('response')[:50]}...")
            passed += 1
        elif dtype == "more_results":
             print("  ✅ PASSED: Triggered Pagination")
             passed += 1
        else:
             print(f"  ❌ FAILED: Unknown type {dtype}")
             failed += 1
             
    except Exception as e:
        print(f"  ❌ FAILED: LLM Error -> {e}")
        failed += 1

print("\n--- STRESS TEST SUMMARY ---")
print(f"Total Tests: {len(questions)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Accuracy: {(passed/len(questions))*100:.2f}%")
