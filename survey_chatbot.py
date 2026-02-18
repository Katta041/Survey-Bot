import streamlit as st
import pandas as pd
import openai
import os

# --- Configuration ---
# Set page title and layout
st.set_page_config(page_title="Survey Data Chatbot", page_icon="🗳️", layout="wide")

# Load API Key (Priority: Secrets -> Env -> Config)
try:
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        from framework_config import OPENAI_API_KEY
        api_key = OPENAI_API_KEY
    
    os.environ["OPENAI_API_KEY"] = api_key
    client = openai.OpenAI(api_key=api_key)
except Exception as e:
    st.error("🔑 API Key Missing! Please add it to `secrets.toml` or `framework_config.py`.")
    st.stop()

# --- Data Loading ---
DATA_PATH = "./audio_samples/transcribed_metadata_sarvam.csv"

@st.cache_data
def load_data(path):
    if not os.path.exists(path):
        return None
    # Load Transcripts
    df_transcripts = pd.read_csv(path)
    
    # Load Excel Data for Election Columns
    excel_path = "./Razole_Overall Data_V2.xlsx"
    if os.path.exists(excel_path):
        try:
            df_excel = pd.read_excel(excel_path, sheet_name='Data')
            # Normalize column names if needed
            # Join on URL
            # df_transcripts['url'] matches df_excel['Audio URL']
            df = pd.merge(df_transcripts, df_excel, left_on='url', right_on='Audio URL', how='left', suffixes=('', '_excel'))
        except Exception as e:
            st.error(f"Error loading Excel data: {e}")
            df = df_transcripts # Fallback
    else:
        df = df_transcripts

    # Ensure relevant columns are string type for filtering
    # Map long questions to aliases for easier access
    column_aliases = {
        'Q10: మీరు 2024 అసెంబ్లీ ఎన్నికలో ఏ పార్టీ కి వోట్ వేశారు?': 'Vote_2024',
        'Q11: YSRCP నియోజకవర్గ  ఇంచార్జి(Constituency Incharge) అందుబాటులో ఉంటున్నారా?': 'Incharge_Status',
        'Q12: ఒకవేళ YSRCP నియోజకవర్గ ఇంచార్జి ని మార్చాల్సి వస్తే ఎవరైతే బాగుంటుంది అని మీరు భావిస్తున్నారు? (ఈ ప్రశ్న 2024 అసెంబ్లీ ఎన్నికలో YSRCPకి ఓటు వేసినవారికి మాత్రమే చూపించబడుతుంది)': 'Incharge_Replacement'
    }
    df.rename(columns=column_aliases, inplace=True)

    for col in ['Q1', 'Caste', 'Age', 'transcript', 'qc_remark', 'Vote_2024', 'Incharge_Status', 'Incharge_Replacement']:
        if col in df.columns:
            df[col] = df[col].astype(str)
            
    # Ensure sample_id exists for pagination
    if 'sample_id' not in df.columns:
        df['sample_id'] = df.index.astype(str)
        
    return df

df = load_data(DATA_PATH)
# ... (rest of filtering)

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_search" not in st.session_state:
    st.session_state.last_search = {"keywords": [], "topic": "", "cited_ids": []}

# --- Sidebar & Settings ---
with st.sidebar:
    st.title("Settings ⚙️")
    language = st.radio("Response Language / భాష:", ["English", "Telugu (తెలుగు)"])
    st.markdown("---")
    st.markdown("**Dataset Info:**")
    st.write(f"Total Records: {len(df)}")
    # st.write(f"Columns: {', '.join(df.columns)}") # Too heavy
    
    st.markdown("---")
    st.subheader("💡 Suggested Questions")
    
    # Bilingual Suggestions
    first_batch = {
        "English": [
            "How many people in Kapu caste have water issues?",
            "What are the major complaints regarding Infrastructure?",
            "Why are people unhappy with the current Incharge?",
            "Is there corruption reported in welfare schemes?"
        ],
        "Telugu (తెలుగు)": [
            "కాపు కులంలో నీటి సమస్యలు ఉన్నవారెందరు?",
            "మౌలిక సదుపాయాల (రోడ్లు, నీరు) పై ప్రధాన ఫిర్యాదులు ఏమిటి?",
            "ప్రస్తుత ఇంచార్జ్ పై ప్రజలకు అసంతృప్తి ఎందుకు ఉంది?",
            "సంక్షేమ పథకాలలో లంచం అడుగుతున్నారా?"
        ]
    }
    
    # Toggle for more
    if "more_questions" not in st.session_state:
        st.session_state.more_questions = False

    suggestions = first_batch
    
    second_batch = {
        "English": [
            "What is the feedback on the Volunteer system?",
            "Summarize the sentiment towards Jagan (CM).",
            "What are the key issues faced by the Kapu community?",
            "How many people voted for TDP?"
        ],
        "Telugu (తెలుగు)": [
            "వాలంటీర్ల వ్యవస్థ పై ప్రజల అభిప్రాయం ఏమిటి?",
            "ముఖ్యమంత్రి జగన్ గారి పాలన ఎలా ఉంది?",
            "కాపు సామాజిక వర్గం ఎదుర్కొంటున్న ప్రధాన సమస్యలు ఏమిటి?",
            "TDP కి ఎంతమంది ఓటు వేశారు?"
        ]
    }
    
    selected_lang = "Telugu (తెలుగు)" if "Telugu" in language else "English"
    
    # helper to render buttons
    def render_buttons(q_list):
        for q in q_list:
            if st.button(q):
                st.session_state.messages.append({"role": "user", "content": q})
                st.rerun()

    render_buttons(first_batch[selected_lang])
    
    if st.checkbox("Show More Complex Questions ➕"):
        render_buttons(second_batch[selected_lang])

# --- Main Interface ---
st.title("🗳️ Survey Data Intelligence Chatbot")
st.markdown("""
Ask questions about the survey data. 
- **Quantitative:** "How many people in Kapu caste have water issues?"
- **Qualitative:** "What are people saying about the MLA's performance?"
""")

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Logic: Query Processing ---
def generate_response(user_query, lang, history):
    # Get unique values for context
    unique_castes = df['Caste'].unique().tolist()
    unique_problems = df['Q1'].unique().tolist()
    unique_votes = df['Vote_2024'].unique().tolist() if 'Vote_2024' in df.columns else []
    
    # System Prompt for Decision Making
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
    
    Current User Query: "{user_query}"
    Output Language: {lang}
    Previous Context: {history[-3:] if history else "None"}

    DECISION LOGIC:
    1. If the user asks for a COUNT, AGGREGATION, or STATISTIC (e.g., "How many voted for TDP?", "Distribution of Incharge status"):
       - Return a JSON object with: {{"type": "code", "code": "..."}}
       - The 'code' must be valid Python/Pandas code that operates on a dataframe named `df`.
       - Use column aliases `Vote_2024`, `Incharge_Status`, etc.
       - **CRITICAL:** Use `.str.contains` or lists for filtering.
       - **EXAMPLES:**
         - "How many voted YSRCP?" -> `df['Vote_2024'].str.contains('YSRCP').sum()`
         - "Kapu water issues" -> `df[(df['Caste']=='Kapu') & (df['Q1'].isin(['సాగునీరు', 'త్రాగునీరు']))].shape[0]`
    
    2. If the user asks for QUALITATIVE info (e.g., "Why do people want to change the Incharge?"):
       - Return a JSON object with: {{"type": "search", "keywords": ["..."], "topic": "..."}}
       - The 'keywords' should be Telugu terms found in transcripts.
       - **EXAMPLES:** 
         - "MLA Performance" -> ["ఎమ్మెల్యే", "పనితీరు", "బాగుంది", "బాగోలేదు"]
         - "Incharge" -> ["ఇంచార్జ్", "ఇంచార్జి", "మార్చాలి"]
    
    3. If the user asks for MORE info on the previous topic (e.g., "Anything else?", "More examples"):
       - Return a JSON object with: {{"type": "more_results"}}
    
    4. If general chat or follow-up:
       - Return {{"type": "chat", "response": "..."}}
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
        return response.choices[0].message.content
    except Exception as e:
        return f'{{"type": "error", "message": "{str(e)}"}}'

def execute_pandas_code(code, df):
    try:
        # Restricted execution environment
        local_vars = {"df": df, "pd": pd}
        result = eval(code, {}, local_vars)
        return result
    except Exception as e:
        return f"Error executing code: {e}"

def search_transcripts(keywords, topic, df, exclude_ids=[]):
    # Simple keyword search in transcripts
    mask = df['transcript'].str.contains('|'.join(keywords), case=False, na=False)
    matches = df[mask]
    
    # Filter out already seen IDs
    if exclude_ids:
        matches = matches[~matches['sample_id'].isin(exclude_ids)]
    
    if matches.empty:
        return None, [], 0
    
    # Sort matches by length (longer = more likely to contain opinion)
    matches['length'] = matches['transcript'].str.len()
    matches = matches.sort_values('length', ascending=False)
    
    total_matches = len(matches)
    # Sample up to 3 matches for context (Reduced from 5 to avoid Rate Limit)
    sample_matches = matches.head(3)
    context_text = ""
    citations = []
    
    for idx, row in sample_matches.iterrows():
        sid = row.get('sample_id', str(idx))
        text = row['transcript']
        # Truncate to 1500 chars to save tokens
        if len(text) > 1500:
            text = text[:1500] + "... (truncated)"
        context_text += f"[Sample {sid}]: {text}\n\n"
        citations.append(sid)
        
        citations.append(sid)
        
    return context_text, citations, total_matches

def synthesize_qualitative_answer(query, context, lang):
    prompt = f"""
    User Query: {query}
    Context (Telugu Transcripts):
    {context}
    
    Task: Summarize the opinions/information found in these transcripts regarding the query.
    - The transcripts are in Telugu (English script or Telugu script).
    - "Bagundi" / "బాగుంది" = Good / Positive Performance.
    - "Baledu" / "బాగోలేదు" = Bad / Negative Performance.
    - "Dabbu" / "డబ్బు" = Money/Bribe.
    - Cite the source using [Sample ID] for every point.
    - Answer in: {lang}
    - If the context mentions the topic but has no clear opinion, state "Mentioned without specific opinion."
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except openai.RateLimitError:
        return "⚠️ **System Busy:** The request was too large for the current rate limits. I have reduced the context size, please try asking again in a moment."
    except Exception as e:
        return f"Error generating answer: {str(e)}"

# --- User Input ---
# Check if last message is user and needs processing
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_msg = st.session_state.messages[-1]
    # Check if assistant has already responded to this? 
    # Actually, simplistic way: if last is user, generate response
    # But we need to avoid infinite loop. 
    # Streamlit reruns script. We should check if len(messages) is odd (User just added).
    pass

if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# --- Process Last Message if User ---
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    prompt = st.session_state.messages[-1]["content"]
    
    # Assistant Response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing data..."):
            import json
            
            # 1. Decide Strategy
            # Pass simple list of dicts as history
            history_summary = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
            decision_json = generate_response(prompt, language, history_summary)
            decision = json.loads(decision_json)
            
            response_text = ""
            
            if decision["type"] == "code":
                code = decision["code"]
                # st.code(code, language="python") # Optional: Show code for debugging
                result = execute_pandas_code(code, df)
                
                if "Error executing code" in str(result):
                     st.error(f"Code Execution Failed:\n{result}")
                     st.code(code, language="python")
                     response_text = "Sorry, I couldn't calculate that due to a code error. The error details are above."
                else:
                    # Format result into natural language
                    final_prompt = (
                        f"User Question: '{prompt}'\n"
                        f"Data Answer: {result}\n"
                        f"Task: Respond to the user naturally in {language}.\n"
                        f"- Do NOT mention 'code execution', 'dataframe', or 'analysis'.\n"
                        f"- Just state the answer clearly and conversationally.\n"
                        f"- For example: 'There are 207 voters for YSRCP.' instead of 'The code execution reveals...'"
                    )
                final_res = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": final_prompt}]
                )
                response_text = final_res.choices[0].message.content
                
            elif decision["type"] == "search" or decision.get("type") == "more_results":
                if decision["type"] == "search":
                    # New Search
                    keywords = decision["keywords"]
                    topic = decision["topic"]
                    
                    # FALLBACK: If keywords look English, map them to Telugu
                    # This handles cases where LLM ignores the system prompt instructions
                    english_to_telugu = {
                        # --- PARTIES & LEADERS ---
                        "ysrcp": ["YSRCP", "వైసిపి", "ఫ్యాన్", "జగన్"],
                        "tdp": ["TDP", "టిడిపి", "సైకిల్", "బాబు", "చంద్రబాబు"],
                        "jsp": ["JSP", "జనసేన", "పవన్", "గ్లాస్"],
                        "jagan": ["జగన్", "జగనన్న", "CM"],
                        "babu": ["బాబు", "చంద్రబాబు", "CBN"],
                        "pawan": ["పవన్", "కళ్యాణ్"],
                        "mla": ["ఎమ్మెల్యే", "నాయకుడు", "ఇంచార్జి"],
                        "incharge": ["ఇంచార్జ్", "సూర్యారావు"],

                        # --- PERFORMANCE & SENTIMENT ---
                        "performance": ["పనితీరు", "బాగుంది", "బాగోలేదు", "చేస్తున్నారు"],
                        "good": ["బాగుంది", "మంచి", "సూపర్", "పర్లేదు"],
                        "bad": ["బాగోలేదు", "చెత్త", "వెస్ట్", "రాదు"],
                        "change": ["మార్చాలి", "వద్దు", "ఓడిపోతారు"],
                        "win": ["గెలుస్తారు", "గెలుపు"],

                        # --- INFRASTRUCTURE ---
                        "roads": ["రోడ్లు", "రోడ్డు", "గుంతలు", "దారి"],
                        "water": ["నీరు", "త్రాగునీరు", "మంచినీరు", "కొళాయి", "సమస్య"],
                        "power": ["కరెంట్", "లైటు", "స్తంభం", "వెలుగు"],
                        "drainage": ["డ్రైనేజ్", "కాలువ", "మురికి"],
                        "housing": ["ఇల్లు", "స్థలాలు", "కాలనీ", "జగనన్న కాలనీ"],

                        # --- SCHEMES ---
                        "pension": ["పెన్షన్", "పింఛన్", "చెస్ట్"],
                        "scheme": ["పథకం", "లబ్ది", "అర్హత"],
                        "ration": ["రేషన్", "బియ్యం", "కందిపప్పు"],
                        "amma vodi": ["అమ్మ ఒడి"],
                        "cheyutha": ["చేయూత"],
                        "vidya deevena": ["విద్యా దీవెన", "ఫీజు"],
                        "rythu": ["రైతు", "భరోసా"],
                        "volunteer": ["వాలంటీర్", "వాలంటీర్లు"],
                        "secretariat": ["సచివాలయం", "ఆఫీసు"],

                        # --- ISSUES ---
                        "money": ["డబ్బు", "లంచం", "రేట్లు"],
                        "corruption": ["లంచం", "డబ్బు", "కమిషన్"],
                        "jobs": ["ఉద్యోగం", "పని", "కూలి"],
                        "prices": ["ధరలు", "రేట్లు"]
                    }
                    
                    expanded_keywords = set(keywords)
                    for k in keywords:
                        k_lower = k.lower()
                        for eng_key, tel_vals in english_to_telugu.items():
                            if eng_key in k_lower:
                                expanded_keywords.update(tel_vals)
                    
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

