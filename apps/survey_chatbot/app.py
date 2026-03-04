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
PROD_DATA_PATH = Config.PRODUCTION_DATA_DIR / "tn_survey_sanitized.csv"
RAW_TRANSCRIPT_PATH = Config.AUDIO_DIR / "tn_samples/tn_transcribed_metadata_sarvam.csv"
RAW_EXCEL_PATH = Config.RAW_DATA_DIR / "Tamil Nadu/THIRUVOTTIYUR_2026-02-19_to_2026-02-20.xlsx"

@st.cache_data
def load_data():
    # 1. Try Sanitized Production Data first (Recommended for Cloud)
    if os.path.exists(PROD_DATA_PATH):
        df = pd.read_csv(PROD_DATA_PATH)
    
    # 2. Fallback to Raw Local Files & Merging
    elif os.path.exists(RAW_TRANSCRIPT_PATH):
        df_transcripts = pd.read_csv(RAW_TRANSCRIPT_PATH)
        if os.path.exists(RAW_EXCEL_PATH):
            try:
                df_excel = pd.read_excel(RAW_EXCEL_PATH)
                # Map Excel columns to application standard
                mapping = {
                    'Audio URL': 'url',
                    'Q1: உங்கள் தொகுதி சட்டமன்ற உறுப்பினரின் (MLA) செயல்பாடுகளால் நீங்கள் திருப்தியாக உள்ளீர்களா?/ Are you satisfied with the performance of your constituency MLA?': 'MLA_Satisfaction',
                    'Q2: வரவிருக்கும் சட்டமன்ற தேர்தலில் ஆட்சி மாற்றம் தேவையென நீங்கள் நினைக்கிறீர்களா?/ Do you feel a change in government is needed in the coming assembly Elections?': 'Desires_Change',
                    'Q3: தமிழ்நாட்டின் அடுத்த முதலமைச்சராக நீங்கள் யாரை ஆதரிக்கிறீர்கள்?/ Whom do you support as Tamil Nadu’s next Chief Minister?': 'Next_CM',
                    'Q4: வரவிருக்கும் சட்டமன்ற தேர்தலில் நீங்கள் எந்தக் கட்சி / கூட்டணிக்கு வாக்களிக்க உள்ளீர்கள்?/ Which party/ alliance will you vote in the upcoming assembly elections?': 'Vote_2026',
                    'Q9: பாலினம்/Gender': 'Gender_Excel',
                    'Q10: வயது பிரிவு/Age Group': 'Age_Group',
                    'Q13: சாதி/Caste': 'Caste_Excel'
                }
                df_excel_safe = df_excel[list(mapping.keys())].rename(columns=mapping)
                df = pd.merge(df_transcripts, df_excel_safe, on='url', how='left')
                
                # Harmonize columns
                if 'Gender' in df.columns and 'Gender_Excel' in df.columns:
                    df['Gender'] = df['Gender'].fillna(df['Gender_Excel'])
                if 'Caste' in df.columns and 'Caste_Excel' in df.columns:
                    df['Caste'] = df['Caste'].fillna(df['Caste_Excel'])
            except Exception as e:
                st.warning(f"⚠️ Failed to merge Excel data: {e}")
                df = df_transcripts
        else:
            df = df_transcripts
    else:
        st.error(f"❌ No data found at {PROD_DATA_PATH} or {RAW_TRANSCRIPT_PATH}")
        return None

    # Ensure relevant columns are string type for filtering
    columns_to_str = ['MLA_Satisfaction', 'Next_CM', 'Vote_2026', 'Caste', 'transcript']
    for col in columns_to_str:
        if col in df.columns:
            df[col] = df[col].astype(str).fillna("Unknown")
            
    # Ensure sample_id exists for pagination
    if 'sample_id' not in df.columns:
        df['sample_id'] = df.index.astype(str)
        
    df = df.loc[:, ~df.columns.duplicated()]
    return df

df = load_data()
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
    
    # Dataset Info
    st.markdown("**📍 Constituency:** Thiruvottiyur, Chennai")
    st.markdown("**📅 Survey Period:** Feb 19–20, 2026")
    if df is not None:
        st.markdown(f"**🎙️ Respondents:** {len(df):,}")
        if 'Next_CM' in df.columns:
            top_cm = df['Next_CM'].value_counts().index[0].split('/')[-1].strip() if len(df['Next_CM'].value_counts()) > 0 else "N/A"
            st.markdown(f"**🏆 Top CM Pick:** {top_cm}")
        if 'Vote_2026' in df.columns:
            top_party = df['Vote_2026'].value_counts().index[0].split('/')[-1].strip() if len(df['Vote_2026'].value_counts()) > 0 else "N/A"
            st.markdown(f"**🗳️ Top Party:** {top_party}")
    
    st.markdown("---")
    st.subheader("💡 Suggested Questions")
    
    selected_lang = "Tamil (தமிழ்)" if "Tamil" in language else "English"
    suggestions = {
        "English": [
            "Who do people support for next CM?",
            "Which party will people vote for in 2026?",
            "Are people satisfied with the MLA?",
            "Do people want a change in government?",
            "Break down CM support by caste",
            "How do women vote vs men?",
            "What do people say about Vijay (TVK)?",
            "What are people's main concerns?",
            "What do people say about DMK government schemes?",
            "Show TVK vs DMK support numbers",
        ],
        "Tamil (தமிழ்)": [
            "அடுத்த முதல்வராக யாரை மக்கள் ஆதரிக்கிறார்கள்?",
            "2026 தேர்தலில் எந்த கட்சிக்கு வாக்களிப்பார்கள்?",
            "மக்கள் எம்.எல்.ஏ திருப்தியாக இருக்கிறார்களா?",
            "ஆட்சி மாற்றம் வேண்டும் என்று நினைக்கிறார்களா?",
            "சாதி வாரியாக முதல்வர் ஆதரவு என்ன?",
            "விஜய் (த.வெ.க) பற்றி மக்கள் என்ன சொல்கிறார்கள்?",
            "மக்களின் முக்கிய கோரிக்கைகள் என்ன?",
            "திமுக அரசு திட்டங்களை பற்றி என்ன சொல்கிறார்கள்?",
        ]
    }
    
    for i, q in enumerate(suggestions[selected_lang]):
        if st.button(q, key=f"sugg_{selected_lang[:2]}_{i}"):
            st.session_state.messages.append({"role": "user", "content": q})
            st.rerun()

# --- Main Interface ---
st.title("🗳️ Thiruvottiyur Constituency — Survey Intelligence Chatbot")
st.markdown(
    "**📍 Thiruvottiyur, Chennai** &nbsp;|&nbsp; "
    f"**🎙️ {len(df):,} Respondents** &nbsp;|&nbsp; "
    "**📅 Feb 19–20, 2026**"
    if df is not None else ""
)
st.markdown("Ask any question about the survey data in natural language — statistics, opinions, or qualitative insights.")

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
