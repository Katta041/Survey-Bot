import streamlit as st
import pandas as pd
import openai
import os
try:
    import telemetry as _tel
except Exception:
    _tel = None

# --- Configuration ---
# Set page title and layout
st.set_page_config(page_title="Survey Data Chatbot", page_icon="🗳️", layout="wide")

# Load API Key (Priority: Secrets -> Env -> Config)
api_key = None
try:
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    pass

if not api_key:
    try:
        import sys
        # Ensure current directory is in path to find framework_config
        if os.getcwd() not in sys.path:
            sys.path.append(os.getcwd())
        from framework_config import OPENAI_API_KEY
        api_key = OPENAI_API_KEY
    except Exception as e:
        print(f"Failed to load from framework_config: {e}")

if not api_key:
    st.error("🔑 API Key Missing! Please add it to `.streamlit/secrets.toml` or `framework_config.py`.")
    st.stop()

os.environ["OPENAI_API_KEY"] = api_key
client = openai.OpenAI(api_key=api_key)

# --- Data Loading ---
# --- Data Loading ---
# Use relative paths for Cloud Deployment
DATA_PATH = "audio_samples/tn_samples/tn_transcribed_metadata_sarvam.csv"

@st.cache_data
def load_data(path):
    if not os.path.exists(path):
        st.error(f"❌ Data file not found at: {path}")
        return None
    # Load Transcripts
    df_transcripts = pd.read_csv(path)
    
    # Load Excel Data for Election Columns
    excel_path = "Tamil Nadu/THIRUVOTTIYUR_2026-02-19_to_2026-02-20.xlsx"
    if os.path.exists(excel_path):
        try:
            df_excel = pd.read_excel(excel_path) # Auto-picks first sheet
            # Normalize column names if needed
            # Drop columns from df_transcripts that we will get from Excel
            cols_to_drop = ['Caste', 'Age', 'Gender', 'Q1_MLA', 'Q3_Next_CM']
            for c in cols_to_drop:
                if c in df_transcripts.columns:
                    df_transcripts.drop(columns=[c], inplace=True)
                    
            df = pd.merge(df_transcripts, df_excel, left_on='url', right_on='Audio URL', how='left', suffixes=('', '_excel'))
        except Exception as e:
            st.error(f"Error loading Excel data: {e}")
            df = df_transcripts # Fallback
    else:
        st.warning(f"⚠️ Excel data not found at: {excel_path}. Using transcripts only.")
        df = df_transcripts

    # Ensure relevant columns are string type for filtering
    # Map long questions to aliases for easier access
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

    columns_to_str = ['MLA_Satisfaction', 'Desires_Change', 'Next_CM', 'Vote_2026', 'Vote_2021', 'Caste', 'Gender', 'Age_Group', 'transcript', 'QC Comment']
    for col in columns_to_str:
        if col in df.columns:
            df[col] = df[col].astype(str)
            
    # Ensure sample_id exists for pagination
    if 'sample_id' not in df.columns:
        df['sample_id'] = df.index.astype(str)
        
    # Deduplicate columns if any still exist
    df = df.loc[:, ~df.columns.duplicated()]
        
    return df

df = load_data(DATA_PATH)
# ... (rest of filtering)

# Initialise Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_search" not in st.session_state:
    st.session_state.last_search = {"keywords": [], "topic": "", "cited_ids": []}

# --- Sidebar & Settings ---
with st.sidebar:
    st.title("Settings ⚙️")
    language = st.radio("Response Language / மொழி:", ["English", "Tamil (தமிழ்)"])
    st.markdown("---")
    st.markdown("**Dataset Info:**")
    if df is None:
        st.error("❌ Failed to load data. Please check if the data files exist in the repository.")
        st.stop()
    
    # Display Metrics
    st.write(f"Total Records: {len(df)}")
    
    st.markdown("---")
    st.subheader("💡 Suggested Questions")
    
    # Bilingual Suggestions
    first_batch = {
        "English": [
            "Are people satisfied with the MLA's performance?",
            "Who do people support as the next Chief Minister?",
            "Why do people want a change in government?",
            "What did people say about Vijay (TVK)?"
        ],
        "Tamil (தமிழ்)": [
            "எம்.எல்.ஏ வின் செயல்பாடுகளில் மக்கள் திருப்தி அடைந்துள்ளார்களா?",
            "அடுத்த முதலமைச்சராக மக்கள் யாரை ஆதரிக்கிறார்கள்?",
            "மக்கள் ஏன் ஆட்சி மாற்றத்தை விரும்புகிறார்கள்?",
            "விஜய் (த.வெ.க) பற்றி மக்கள் என்ன சொல்கிறார்கள்?"
        ]
    }
    
    if "more_questions" not in st.session_state:
        st.session_state.more_questions = False

    suggestions = first_batch
    
    second_batch = {
        "English": [
            "What are the main issues faced by women (Female voters)?",
            "How many voters support DMK alliance?",
            "Summarize the sentiment towards the current CM.",
            "Who is considered the most accessible leader?"
        ],
        "Tamil (தமிழ்)": [
            "பெண்கள் எதிர்கொள்ளும் முக்கிய பிரச்சனைகள் என்ன?",
            "திமுக கூட்டணிக்கு எவ்வளவு பேர் ஆதரவு அளிக்கின்றனர்?",
            "தற்போதைய முதல்வரைப் பற்றிய மக்களின் கருத்தை சுருக்கமாகக் கூறவும்.",
            "மக்கள் எளிதாக அணுகக்கூடிய தலைவராக யார் கருதப்படுகிறார்?"
        ]
    }
    
    selected_lang = "Tamil (தமிழ்)" if "Tamil" in language else "English"
    
    def render_buttons(q_list):
        for q in q_list:
            if st.button(q):
                st.session_state.messages.append({"role": "user", "content": q})
                st.rerun()

    render_buttons(first_batch[selected_lang])
    
    if st.checkbox("Show More Complex Questions ➕"):
        render_buttons(second_batch[selected_lang])

# --- Main Interface ---
st.title("🗳️ Survey Data Intelligence Chatbot (TN)")
st.markdown("""
Ask questions about the survey data. 
- **Quantitative:** "How many people in Vanniyar caste support TVK?"
- **Qualitative:** "What are people saying about the MLA's performance?"
""")

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Logic: Query Processing ---
def generate_response(user_query, lang, history):
    unique_castes = df['Caste'].unique().tolist() if 'Caste' in df.columns else []
    unique_next_cm = df['Next_CM'].unique().tolist() if 'Next_CM' in df.columns else []
    unique_vote = df['Vote_2026'].unique().tolist() if 'Vote_2026' in df.columns else []
    
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
    
    ### DATASET VOCABULARY (Colloquial Tamil Terms):
    - **Infrastructure:**
      - Roads: "சாலை" (Road), "ரோடு" (Road), "குழிகள்" (Potholes)
      - Water: "தண்ணீர்" (Water), "குடிநீர்" (Drinking Water), "குழாய்" (Tap)
      - Power: "மின்சாரம்" (Electricity), "கரண்ட்" (Current)
    - **Schemes:**
      - "திட்டம்" (Scheme), "உதவித்தொகை" (Pension), "ரேஷன்" (Ration)
    - **Leaders & Parties:**
      - "திமுக" (DMK), "அதிமுக" (ADMK), "விஜய்" (Vijay), "த.வெ.க" (TVK), "ஸ்டாலின்" (Stalin), "எடப்பாடி" (Edappadi)
      - "எம்.எல்.ஏ" (MLA), "முதல்வர்" (CM), "கட்சி" (Party)
    - **Sentiment:**
      - Positive: "நல்லா இருக்கு" (Good), "பரவாயில்லை" (Okay/Not bad), "திருப்தி" (Satisfied)
      - Negative: "மோசம்" (Bad), "ஒன்னும் இல்ல" (Nothing), "திருப்தி இல்லை" (Not satisfied)
      - Change: "மாற்றம் தேவை" (Need change), "வேண்டாம்" (Don't want)

    ### SCHEMA MAPPING:
    - **Caste:** {unique_castes}
    - **Next_CM:** {unique_next_cm}
    - **Vote_2026:** {unique_vote}
    
    Current User Query: "{user_query}"
    Output Language: {lang}
    Previous Context: {history[-3:] if history else "None"}

    DECISION LOGIC:
    1. If the user asks for a COUNT, AGGREGATION, or STATISTIC (e.g., "How many voted for TVK?", "Distribution of next CM"):
       - Return a JSON object with: {{"type": "code", "code": "..."}}
       - The 'code' must be valid Python/Pandas code that operates on a dataframe named `df`.
       - Use column aliases `Next_CM`, `Vote_2026`, etc.
       - **CRITICAL:** Use `.str.contains` or lists for filtering. Because columns contain Tamil/English mixed like 'விஜய் (தமிழகம் வெற்றி கழகம்)/ Vijay (TVK)' use `.str.contains('Vijay')` or `.str.contains('விஜய்')`.
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
    
    try:
        if _tel:
            _s = _tel.Span(); _s.__enter__()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            response_format={"type": "json_object"}
        )
        if _tel:
            _s.__exit__(None, None, None)
            u = response.usage
            _tel.log_llm_call(
                app_name="survey_chatbot_tn",
                user_query=user_query[:400],
                response=response.choices[0].message.content[:300],
                model="gpt-4o",
                input_tokens=u.prompt_tokens if u else 0,
                output_tokens=u.completion_tokens if u else 0,
                latency_ms=_s.latency_ms,
                query_type="decision",
            )
        return response.choices[0].message.content
    except Exception as e:
        return f'{{"type": "error", "message": "{str(e)}"}}'

def execute_pandas_code(code, df):
    try:
        local_vars = {"df": df, "pd": pd}
        # Try evaluating as a single expression first
        try:
            result = eval(code, {}, local_vars)
            return result
        except SyntaxError:
            # If it's a multi-line statement, use exec
            exec(code, {}, local_vars)
            if 'result' in local_vars:
                return local_vars['result']
            # Find the last defined variable that isn't a module
            result = None
            for key, val in reversed(list(local_vars.items())):
                if key not in ['df', 'pd'] and not isinstance(val, type(pd)):
                    result = val
                    break
            return result
    except Exception as e:
        return f"Error executing code: {e}"

def search_transcripts(keywords, topic, df, exclude_ids=[]):
    mask = df['transcript'].str.contains('|'.join(keywords), case=False, na=False)
    matches = df[mask]
    
    if exclude_ids:
        matches = matches[~matches['sample_id'].isin(exclude_ids)]
    
    if matches.empty:
        return None, [], 0
    
    matches['length'] = matches['transcript'].str.len()
    matches = matches.sort_values('length', ascending=False)
    
    total_matches = len(matches)
    sample_matches = matches.head(3)
    context_text = ""
    citations = []
    
    for idx, row in sample_matches.iterrows():
        sid = row.get('sample_id', str(idx))
        text = row['transcript']
        if len(text) > 1500:
            text = text[:1500] + "... (truncated)"
        context_text += f"[Sample {sid}]: {text}\n\n"
        citations.append(sid)
        
    return context_text, citations, total_matches

def synthesize_qualitative_answer(query, context, lang):
    prompt = f"""
    User Query: {query}
    Context (Tamil Transcripts):
    {context}
    
    Task: Summarize the opinions/information found in these transcripts regarding the query.
    - The transcripts are in Tamil.
    - Cite the source using [Sample ID] for every point.
    - Answer in: {lang}
    - If the context mentions the topic but has no clear opinion, state "Mentioned without specific opinion."
    """
    try:
        if _tel:
            _s = _tel.Span(); _s.__enter__()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        if _tel:
            _s.__exit__(None, None, None)
            u = response.usage
            _tel.log_llm_call(
                app_name="survey_chatbot_tn",
                user_query=query[:400],
                response=response.choices[0].message.content[:300],
                model="gpt-4o",
                input_tokens=u.prompt_tokens if u else 0,
                output_tokens=u.completion_tokens if u else 0,
                latency_ms=_s.latency_ms,
                query_type="qualitative_synthesis",
            )
        return response.choices[0].message.content
    except openai.RateLimitError:
        return "⚠️ **System Busy:** Rate limit hit. I have reduced the context size, try asking again."
    except Exception as e:
        return f"Error generating answer: {str(e)}"

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    pass

if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    prompt = st.session_state.messages[-1]["content"]
    
    with st.chat_message("assistant"):
        with st.spinner("Analyzing data..."):
            import json
            
            history_summary = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
            decision_json = generate_response(prompt, language, history_summary)
            decision = json.loads(decision_json)
            
            response_text = ""
            
            if decision["type"] == "code":
                code = decision["code"]
                result = execute_pandas_code(code, df)
                
                if "Error executing code" in str(result):
                     st.error(f"Code Execution Failed:\n{result}")
                     st.code(code, language="python")
                     response_text = "Sorry, I couldn't calculate that due to a code error."
                else:
                    final_prompt = (
                        f"User Question: '{prompt}'\n"
                        f"Data Answer: {result}\n"
                        f"Task: Respond to the user naturally in {language}.\n"
                        f"- Do NOT mention 'code execution', 'dataframe', or 'analysis'.\n"
                        f"- Just state the answer clearly and conversationally."
                    )
                    final_res = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": final_prompt}]
                    )
                    response_text = final_res.choices[0].message.content
                
            elif decision["type"] == "search" or decision.get("type") == "more_results":
                if decision["type"] == "search":
                    keywords = decision["keywords"]
                    topic = decision["topic"]
                    
                    english_to_tamil = {
                        "ysrcp": ["திமுக", "DMK"], # Mapped for analogy, though it's TN so DMK
                        "dmk": ["திமுக", "ஸ்டாலின்", "உதயநிதி"],
                        "admk": ["அதிமுக", "எடப்பாடி", "இரட்டை இலை"],
                        "tvk": ["த.வெ.க", "விஜய்", "தளபதி"],
                        "stalin": ["ஸ்டாலின்", "முதல்வர்"],
                        "vijay": ["விஜய்", "ஜோசப் விஜய்"],
                        "mla": ["எம்.எல்.ஏ", "சட்டமன்ற உறுப்பினர்"],
                        "performance": ["செயல்பாடு", "திருப்தி", "பணி"],
                        "good": ["நல்லா இருக்கு", "பரவாயில்லை", "திருப்தி"],
                        "bad": ["மோசம்", "திருப்தி இல்லை", "ஒன்னும் இல்ல"],
                        "change": ["மாற்றம் தேவை", "வேண்டாம்", "புதுசு"],
                        "water": ["தண்ணீர்", "குடிநீர்", "குழாய்"],
                        "roads": ["சாலை", "ரோடு", "குழிகள்"],
                        "power": ["மின்சாரம்", "கரண்ட்"],
                        "scheme": ["திட்டம்", "உதவி", "ரேஷன்"]
                    }
                    
                    expanded_keywords = set(keywords)
                    for k in keywords:
                        k_lower = k.lower()
                        for eng_key, tam_vals in english_to_tamil.items():
                            if eng_key in k_lower:
                                expanded_keywords.update(tam_vals)
                    
                    keywords = list(expanded_keywords)

                    exclude_ids = []
                    # Reset session state
                    st.session_state.last_search = {"keywords": keywords, "topic": topic, "cited_ids": []}
                else:
                    # More Results (Pagination)
                    keywords = st.session_state.last_search["keywords"]
                    topic = st.session_state.last_search["topic"]
                    exclude_ids = st.session_state.last_search["cited_ids"]
                    if not keywords:
                        response_text = "I don't have a previous search context to load more results for."
                        keywords = [] # Break

                context, citations, total_matches = search_transcripts(keywords, topic, df, exclude_ids)
                
                if context:
                    # Update cited IDs
                    st.session_state.last_search["cited_ids"].extend(citations)
                    
                    if decision["type"] == "more_results":
                        response_text = synthesize_qualitative_answer(f"Provide MORE details on {topic} (different from previous)", context, language)
                    else:
                        response_text = synthesize_qualitative_answer(prompt, context, language)
                else:
                    if decision["type"] == "more_results":
                         response_text = f"No *more* transcripts found for '{topic}'."
                    else:
                         response_text = f"No transcripts found containing keywords: {', '.join(keywords)}"
            
            else: # Chat or Error
                response_text = decision.get("response", decision.get("message", "Error processing request."))

            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})

            # Debug Info
            with st.expander("🛠️ Debug Info (Internal State)"):
                st.write(f"**Decision Type:** {decision.get('type')}")
                if decision.get("type") in ["search", "more_results"]:
                    st.write(f"**Topic:** {st.session_state.last_search.get('topic')}")
                    st.write(f"**Keywords:** {st.session_state.last_search.get('keywords')}")
                    st.write(f"**Total Matches Available:** {total_matches if 'total_matches' in locals() else 'N/A'}")
                    st.write(f"**Cited IDs (Previous + New):** {st.session_state.last_search.get('cited_ids')}")
                    st.text_area("Context Sent to LLM:", value=context if context else "None", height=200)
                    # st.write(f"**Matches Found:** {len(context) if context else 0}")

