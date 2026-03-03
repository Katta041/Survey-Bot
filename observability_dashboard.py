"""
observability_dashboard.py — Local Observability Dashboard
Queries OpenAI Organization Usage API + estimates Sarvam costs from local logs.
Run with: streamlit run observability_dashboard.py
"""
import streamlit as st
import pandas as pd
import requests
import datetime
import json
import os
from collections import defaultdict

st.set_page_config(
    page_title="📡 API Observability Dashboard",
    page_icon="📡",
    layout="wide"
)

# ─── Dark Pro CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

.stApp { background-color: #0f172a; font-family: 'Inter', sans-serif; }
h1,h2,h3,h4 { color: #e2e8f0 !important; }
p, li, label { color: #94a3b8 !important; }
.stSelectbox label, .stDateInput label { color: #94a3b8 !important; }
.stDataFrame { border-radius: 10px; overflow: hidden; }
div[data-testid="metric-container"] {
    background: linear-gradient(135deg, #1e293b, #0f172a);
    padding: 16px 20px;
    border-radius: 12px;
    border-left: 4px solid #3b82f6;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}
div[data-testid="metric-container"] > label { color: #94a3b8 !important; font-size: 0.8em; }
div[data-testid="metric-container"] > div { color: #60a5fa !important; font-size: 1.6em; font-weight: 700; }
.stTabs [data-baseweb="tab"] { color: #94a3b8; }
.stTabs [aria-selected="true"] { color: #60a5fa !important; border-bottom: 2px solid #3b82f6; }
section[data-testid="stSidebar"] { background: #1e293b; }
section[data-testid="stSidebar"] label { color: #94a3b8 !important; }
.section-header {
    font-size: 1.1em; font-weight: 600; color: #e2e8f0;
    border-bottom: 1px solid #334155; padding-bottom: 8px; margin: 24px 0 16px 0;
}
</style>
""", unsafe_allow_html=True)

# ─── Sidebar Config ────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuration")
    st.markdown("---")

    openai_key = st.text_input("OpenAI API Key", type="password",
        value=os.environ.get("OPENAI_API_KEY", ""),
        help="Used to fetch from OpenAI Usage API")

    sarvam_key = st.text_input("Sarvam API Key", type="password",
        value="",
        help="Sarvam has no public usage API — cost is estimated from local logs")

    st.markdown("---")
    st.markdown("**Date Range**")
    today = datetime.date.today()
    start_date = st.date_input("From", value=today - datetime.timedelta(days=30))
    end_date   = st.date_input("To",   value=today)

    st.markdown("---")
    app_names = ["All Apps", "Audio Insight Engine", "Survey Chatbot TN"]
    selected_app = st.selectbox("App Filter", app_names)

    st.markdown("---")
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ─── OpenAI Usage API ─────────────────────────────────────────────────────────
OPENAI_COST = {
    "gpt-4o":            {"input": 2.50,  "output": 10.00},
    "gpt-4o-mini":       {"input": 0.15,  "output": 0.60},
    "gpt-4-turbo":       {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo":     {"input": 0.50,  "output": 1.50},
    "whisper-1":         {"input": 0.006, "output": 0},  # per minute, mapped as input
}
SARVAM_COST_PER_MIN = 0.005  # USD/min estimate

@st.cache_data(ttl=120, show_spinner=False)
def fetch_openai_usage(api_key: str, start: datetime.date, end: datetime.date):
    """Fetch daily completions usage via OpenAI /v1/usage endpoint."""
    all_rows = []
    date_cursor = start
    headers = {"Authorization": f"Bearer {api_key}"}

    while date_cursor <= end:
        date_str = date_cursor.strftime("%Y-%m-%d")
        try:
            resp = requests.get(
                "https://api.openai.com/v1/usage",
                headers=headers,
                params={"date": date_str},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                for entry in data.get("data", []):
                    model = entry.get("snapshot_id", "unknown")
                    n_context = entry.get("n_context_tokens_total", 0)
                    n_generated = entry.get("n_generated_tokens_total", 0)
                    n_requests = entry.get("n_requests", 0)
                    rates = OPENAI_COST.get(model.split(":")[0], {"input": 2.50, "output": 10.00})
                    cost = (n_context * rates["input"] + n_generated * rates["output"]) / 1_000_000
                    all_rows.append({
                        "date": date_str,
                        "model": model,
                        "requests": n_requests,
                        "input_tokens": n_context,
                        "output_tokens": n_generated,
                        "cost_usd": round(cost, 6),
                    })
        except Exception:
            pass
        date_cursor += datetime.timedelta(days=1)

    return pd.DataFrame(all_rows) if all_rows else pd.DataFrame(
        columns=["date","model","requests","input_tokens","output_tokens","cost_usd"])


def load_sarvam_local_log():
    """
    Reads local Sarvam call log if it exists.
    The log is a JSONL file written by the apps in append mode.
    Falls back to an empty dataframe if not present.
    """
    log_path = os.path.join(os.path.dirname(__file__), "sarvam_usage_log.jsonl")
    rows = []
    if os.path.exists(log_path):
        with open(log_path) as f:
            for line in f:
                try:
                    rows.append(json.loads(line.strip()))
                except Exception:
                    pass
    if rows:
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.date
        return df
    return pd.DataFrame(columns=["date","app","audio_duration_sec","num_chunks","language_code","timestamp"])


# ─── Fetch Data ───────────────────────────────────────────────────────────────
st.title("📡 API Observability Dashboard")
st.markdown("Live OpenAI usage + Sarvam cost estimates — select an app and date range in the sidebar.")
st.markdown("---")

if not openai_key:
    st.warning("⚠️ Enter your OpenAI API Key in the sidebar to load data.")
    st.stop()

with st.spinner("Fetching OpenAI usage data..."):
    oai_df = fetch_openai_usage(openai_key, start_date, end_date)

sarvam_df = load_sarvam_local_log()

# Filter sarvam by date
if not sarvam_df.empty and "date" in sarvam_df.columns:
    sarvam_df = sarvam_df[
        (sarvam_df["date"] >= start_date) & (sarvam_df["date"] <= end_date)
    ]

# ─── Key Metrics ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🔭 Overall Summary</div>', unsafe_allow_html=True)

total_oai_cost = oai_df["cost_usd"].sum() if not oai_df.empty else 0
total_sarvam_min = (sarvam_df["audio_duration_sec"].sum() / 60) if not sarvam_df.empty and "audio_duration_sec" in sarvam_df.columns else 0
total_sarvam_cost = total_sarvam_min * SARVAM_COST_PER_MIN
total_cost = total_oai_cost + total_sarvam_cost
total_requests = int(oai_df["requests"].sum()) if not oai_df.empty else 0
total_tokens = int((oai_df["input_tokens"].sum() + oai_df["output_tokens"].sum())) if not oai_df.empty else 0
sarvam_calls = len(sarvam_df) if not sarvam_df.empty else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("💰 Total Cost (USD)", f"${total_cost:.4f}")
c2.metric("🤖 OpenAI Cost",      f"${total_oai_cost:.4f}")
c3.metric("🎙️ Sarvam Cost (est.)", f"${total_sarvam_cost:.4f}")
c4.metric("📞 LLM Requests",     f"{total_requests:,}")
c5.metric("🔤 Total Tokens",     f"{total_tokens:,}")

st.markdown("---")

# ─── OpenAI Section ───────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🤖 OpenAI Usage</div>', unsafe_allow_html=True)

if oai_df.empty:
    st.info("No OpenAI usage data found for this date range.")
else:
    tab1, tab2, tab3 = st.tabs(["📅 Daily Cost", "📊 By Model", "📋 Raw Data"])

    with tab1:
        daily_cost = oai_df.groupby("date")["cost_usd"].sum().reset_index()
        daily_cost.columns = ["Date", "Cost (USD)"]
        st.line_chart(daily_cost.set_index("Date"))

    with tab2:
        model_summary = oai_df.groupby("model").agg(
            Requests=("requests", "sum"),
            Input_Tokens=("input_tokens", "sum"),
            Output_Tokens=("output_tokens", "sum"),
            Cost_USD=("cost_usd", "sum"),
        ).reset_index().sort_values("Cost_USD", ascending=False)
        model_summary["Cost_USD"] = model_summary["Cost_USD"].round(6)
        st.dataframe(model_summary, use_container_width=True)
        st.bar_chart(model_summary.set_index("model")["Cost_USD"])

    with tab3:
        st.dataframe(oai_df.sort_values("date", ascending=False), use_container_width=True)

st.markdown("---")

# ─── Sarvam Section ───────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🎙️ Sarvam Transcription Usage</div>', unsafe_allow_html=True)

st.info("""
**Note:** Sarvam does not have a public usage API.
Sarvam usage is estimated from a local log file (`sarvam_usage_log.jsonl`) written by your apps.

**To enable Sarvam tracking without modifying the deployed apps:**
You can manually log Sarvam calls from your local `audio_transcription_app.py` by running the app locally and checking the log file.
""")

if sarvam_df.empty:
    st.warning("No Sarvam usage data found. Run the Audio Insight Engine locally to generate logs.")
else:
    s1, s2, s3 = st.columns(3)
    s1.metric("Transcription Calls", f"{sarvam_calls}")
    s2.metric("Total Audio (min)", f"{total_sarvam_min:.1f}")
    s3.metric("Estimated Cost", f"${total_sarvam_cost:.4f}")

    daily_sarvam = sarvam_df.groupby("date").agg(
        Calls=("audio_duration_sec","count"),
        Minutes=("audio_duration_sec","sum"),
    ).reset_index()
    daily_sarvam["Minutes"] = (daily_sarvam["Minutes"] / 60).round(2)
    daily_sarvam["Est_Cost_USD"] = (daily_sarvam["Minutes"] * SARVAM_COST_PER_MIN).round(6)
    st.dataframe(daily_sarvam, use_container_width=True)
    st.bar_chart(daily_sarvam.set_index("date")["Est_Cost_USD"])

st.markdown("---")

# ─── App Context Note ─────────────────────────────────────────────────────────
st.markdown('<div class="section-header">ℹ️ App Reference</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    **🎙️ Audio Insight Engine**
    - URL: `https://survey-bot-crx465aaxrusnn5pjtxh8h.streamlit.app/`
    - Models: `gpt-4o` (analysis), Sarvam `saaras:v3` (transcription)
    """)
with col2:
    st.markdown("""
    **🗳️ Survey Chatbot TN**
    - URL: `https://app-app-kxsuhapap3cjihqm2szeb8.streamlit.app/`
    - Models: `gpt-4o` (decision + synthesis + formatting)
    """)

st.caption(f"Last refreshed: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST  |  OpenAI data has ~2min cache TTL.")
