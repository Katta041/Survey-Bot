import streamlit as st
import pandas as pd
import openai
import os
import sys
from pathlib import Path

# Add project root to path for modular imports
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.core.config import Config
from src.core.telemetry import Span, log_llm_call
from src.logic.chatbot.engine import SurveyChatEngine

# --- Configuration ---
# Set page title and layout
st.set_page_config(page_title="Survey Data Chatbot", page_icon="🗳️", layout="wide")

# Initialize Engine
if "engine" not in st.session_state:
    st.session_state.engine = None

# --- Data Loading ---
# Use Absolute Paths from Config
DATA_PATH = Config.AUDIO_DIR / "tn_samples/tn_transcribed_metadata_sarvam.csv"
EXCEL_PATH = Config.RAW_DATA_DIR / "Tamil Nadu/THIRUVOTTIYUR_2026-02-19_to_2026-02-20.xlsx"

@st.cache_data
def load_data(path):
    if not os.path.exists(path):
        st.error(f"❌ Data file not found at: {path}")
        return None
    # Load Transcripts
    df_transcripts = pd.read_csv(path)
    
    # Load Excel Data for Election Columns
    excel_path = EXCEL_PATH
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

    columns_to_str = ['MLA_Satisfaction', 'Next_CM', 'Vote_2026', 'Caste', 'transcript']
    for col in columns_to_str:
        if col in df.columns:
            df[col] = df[col].astype(str).fillna("Unknown")
            
    # Ensure sample_id exists for pagination
    if 'sample_id' not in df.columns:
        df['sample_id'] = df.index.astype(str)
        
    # Deduplicate columns if any still exist
    df = df.loc[:, ~df.columns.duplicated()]
        
    return df

df = load_data(DATA_PATH)
if df is not None and st.session_state.engine is None:
    st.session_state.engine = SurveyChatEngine(df)

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
    st.write(f"Total Records: {len(df) if df is not None else 0}")
    
    st.markdown("---")
    st.subheader("💡 Suggested Questions")
    
    selected_lang = "Tamil (தமிழ்)" if "Tamil" in language else "English"
    suggestions = {
        "English": ["Are people satisfied with the MLA?", "Who do people support for next CM?", "What do people say about Vijay (TVK)?"],
        "Tamil (தமிழ்)": ["மக்கள் எம்.எல்.ஏ திருப்தியாக இருக்கிறார்களா?", "அடுத்த முதல்வராக யார் வருவார்கள்?", "விஜய் (த.வெ.க) பற்றி மக்கள் என்ன சொல்கிறார்கள்?"]
    }
    
    for q in suggestions[selected_lang]:
        if st.button(q):
            st.session_state.messages.append({"role": "user", "content": q})
            st.rerun()

# --- Main Interface ---
st.title("🗳️ Survey Data Intelligence Chatbot (TN)")
st.markdown("Query thousands of citizen survey transcripts with natural language.")

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# Process User Query
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    prompt = st.session_state.messages[-1]["content"]
    engine = st.session_state.engine
    
    if engine is None:
        st.error("Engine failed to initialize. Check data files.")
        st.stop()

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            history_summary = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-5:]]
            decision = engine.generate_decision(prompt, language, history_summary)
            
            response_text = ""
            
            if decision["type"] == "code":
                result = engine.execute_code(decision["code"])
                response_text = engine.naturalize_data_answer(prompt, result, language)
                
            elif decision["type"] in ["search", "more_results"]:
                if decision["type"] == "search":
                    keywords = decision.get("keywords", [])
                    topic = decision.get("topic", "")
                    exclude_ids = []
                    # Update search state
                    st.session_state.last_search = {"keywords": keywords, "topic": topic, "cited_ids": []}
                else:
                    keywords = st.session_state.last_search["keywords"]
                    topic = st.session_state.last_search["topic"]
                    exclude_ids = st.session_state.last_search["cited_ids"]

                context, citations, total = engine.search_transcripts(keywords, topic, exclude_ids)
                
                if context:
                    st.session_state.last_search["cited_ids"].extend(citations)
                    response_text = engine.synthesize_answer(prompt, context, language)
                else:
                    response_text = f"No transcripts found for '{topic}'."
            
            elif decision["type"] == "chat":
                response_text = decision.get("response", "How can I help you today?")
            else:
                response_text = "I encountered an issue processing that request."

            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})

            # Debug Info
            with st.expander("🛠️ Debug Info"):
                st.write(f"**Decision Type:** {decision.get('type')}")
                if decision.get("type") in ["search", "more_results"]:
                    st.write(f"**Keywords:** {st.session_state.last_search.get('keywords')}")
                    st.write(f"**Matches:** {total if 'total' in locals() else 'N/A'}")
                    # st.write(f"**Matches Found:** {len(context) if context else 0}")
