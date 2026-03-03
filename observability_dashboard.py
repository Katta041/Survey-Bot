"""
observability_dashboard.py — Telemetry Dashboard for Streamlit Apps
Reads from Google Sheets telemetry sink and renders usage, cost, and trace metrics.
"""
import streamlit as st
import pandas as pd
import json
import datetime

st.set_page_config(
    page_title="📡 Observability Dashboard",
    page_icon="📡",
    layout="wide"
)

# --- Custom CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0f172a; }
    h1, h2, h3 { color: #e2e8f0; }
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        border-left: 4px solid #3b82f6;
        margin-bottom: 15px;
    }
    .metric-val { font-size: 2em; font-weight: bold; color: #60a5fa; }
    .metric-label { font-size: 0.85em; color: #94a3b8; margin-top: 4px; }
    .trace-section { background-color: #1e293b; padding: 20px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)


# --- Load Data from Google Sheets ---
@st.cache_data(ttl=60)
def load_telemetry():
    """Loads all telemetry data from Google Sheets. TTL=60s for live refresh."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        sa_json = None
        sheets_id = None
        try:
            if "GOOGLE_SERVICE_ACCOUNT" in st.secrets:
                sa_json = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
                sheets_id = st.secrets["GOOGLE_SHEETS_ID"]
        except Exception:
            pass

        if not sa_json:
            try:
                import framework_config
                sa_json = json.loads(getattr(framework_config, "GOOGLE_SERVICE_ACCOUNT", "null"))
                sheets_id = getattr(framework_config, "GOOGLE_SHEETS_ID", None)
            except Exception:
                pass

        if not sa_json or not sheets_id:
            return None, None, None

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(sa_json, scopes=scopes)
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(sheets_id)

        def _to_df(ws):
            rows = ws.get_all_values()
            if len(rows) < 2:
                return pd.DataFrame()
            return pd.DataFrame(rows[1:], columns=rows[0])

        llm_df = _to_df(spreadsheet.worksheet("llm_traces"))
        sarvam_df = _to_df(spreadsheet.worksheet("sarvam_traces"))
        return llm_df, sarvam_df, None

    except Exception as e:
        return None, None, str(e)


llm_df, sarvam_df, err = load_telemetry()

# --- Header ---
st.title("📡 Observability Dashboard")
st.markdown("Real-time usage, cost, and traceability metrics for all deployed Streamlit apps.")

if err:
    st.error(f"⚠️ Could not connect to Google Sheets: {err}")
    st.info("Add `GOOGLE_SERVICE_ACCOUNT` and `GOOGLE_SHEETS_ID` to your Streamlit secrets to enable live data.")
    st.stop()

if llm_df is None or llm_df.empty:
    st.warning("No telemetry data yet. Use the apps and data will stream here automatically.")
    st.stop()

# --- Preprocess ---
numeric_cols_llm = ["input_tokens", "output_tokens", "cost_usd", "latency_ms"]
for col in numeric_cols_llm:
    if col in llm_df.columns:
        llm_df[col] = pd.to_numeric(llm_df[col], errors="coerce").fillna(0)

if not sarvam_df.empty:
    for col in ["audio_duration_sec", "cost_usd", "latency_ms"]:
        if col in sarvam_df.columns:
            sarvam_df[col] = pd.to_numeric(sarvam_df[col], errors="coerce").fillna(0)

llm_df["date"] = pd.to_datetime(llm_df["timestamp_utc"], errors="coerce").dt.date
total_cost_llm = llm_df["cost_usd"].sum()
total_cost_sarvam = sarvam_df["cost_usd"].sum() if not sarvam_df.empty else 0
total_cost = total_cost_llm + total_cost_sarvam

st.markdown("---")

# --- Overview Metrics ---
st.subheader("🔭 Overall Metrics")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-val">{len(llm_df)}</div>
        <div class="metric-label">Total LLM Calls</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""<div class="metric-card" style="border-left-color:#8b5cf6">
        <div class="metric-val" style="color:#a78bfa">{len(sarvam_df)}</div>
        <div class="metric-label">Sarvam Transcriptions</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""<div class="metric-card" style="border-left-color:#10b981">
        <div class="metric-val" style="color:#34d399">${total_cost:.4f}</div>
        <div class="metric-label">Total API Cost (USD)</div>
    </div>""", unsafe_allow_html=True)

with col4:
    total_tokens = int(llm_df["input_tokens"].sum() + llm_df["output_tokens"].sum())
    st.markdown(f"""<div class="metric-card" style="border-left-color:#f59e0b">
        <div class="metric-val" style="color:#fbbf24">{total_tokens:,}</div>
        <div class="metric-label">Total Tokens Processed</div>
    </div>""", unsafe_allow_html=True)

with col5:
    avg_latency = llm_df["latency_ms"].mean()
    st.markdown(f"""<div class="metric-card" style="border-left-color:#ef4444">
        <div class="metric-val" style="color:#f87171">{avg_latency:.0f}ms</div>
        <div class="metric-label">Avg LLM Latency</div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# --- Per-App Breakdown ---
st.subheader("📱 Per-App Breakdown")
app_group = llm_df.groupby("app_name").agg(
    LLM_Calls=("cost_usd", "count"),
    Total_Cost_USD=("cost_usd", "sum"),
    Avg_Latency_ms=("latency_ms", "mean"),
    Total_Input_Tokens=("input_tokens", "sum"),
    Total_Output_Tokens=("output_tokens", "sum"),
).reset_index()
app_group["Total_Cost_USD"] = app_group["Total_Cost_USD"].round(6)
app_group["Avg_Latency_ms"] = app_group["Avg_Latency_ms"].round(1)
st.dataframe(app_group, use_container_width=True)

st.markdown("---")

# --- Daily Cost / Usage Charts ---
st.subheader("📅 Daily Usage & Cost")

daily = llm_df.groupby(["date", "app_name"]).agg(
    LLM_Calls=("cost_usd", "count"),
    Cost_USD=("cost_usd", "sum"),
    Tokens=("input_tokens", "sum"),
).reset_index()
daily["date"] = daily["date"].astype(str)

tab1, tab2, tab3 = st.tabs(["💰 Daily Cost", "📞 Daily Calls", "🔤 Daily Tokens"])

with tab1:
    pivot_cost = daily.pivot_table(index="date", columns="app_name", values="Cost_USD", aggfunc="sum").fillna(0)
    st.line_chart(pivot_cost)

with tab2:
    pivot_calls = daily.pivot_table(index="date", columns="app_name", values="LLM_Calls", aggfunc="sum").fillna(0)
    st.bar_chart(pivot_calls)

with tab3:
    pivot_tok = daily.pivot_table(index="date", columns="app_name", values="Tokens", aggfunc="sum").fillna(0)
    st.area_chart(pivot_tok)

st.markdown("---")

# --- Trace Table ---
st.subheader("🔍 Full Trace Log (LLM Calls)")
app_filter = st.selectbox("Filter by App", options=["All"] + llm_df["app_name"].unique().tolist())
qtype_filter = st.selectbox("Filter by Query Type", options=["All"] + llm_df["query_type"].unique().tolist())

filtered = llm_df.copy()
if app_filter != "All":
    filtered = filtered[filtered["app_name"] == app_filter]
if qtype_filter != "All":
    filtered = filtered[filtered["query_type"] == qtype_filter]

display_cols = ["timestamp_utc", "app_name", "query_type", "user_query",
                "response_preview", "model", "input_tokens", "output_tokens",
                "cost_usd", "latency_ms", "trace_id"]
st.dataframe(filtered[[c for c in display_cols if c in filtered.columns]].sort_values("timestamp_utc", ascending=False), use_container_width=True)

if not sarvam_df.empty:
    st.markdown("---")
    st.subheader("🎙️ Sarvam Transcription Traces")
    st.dataframe(sarvam_df.sort_values("timestamp_utc", ascending=False), use_container_width=True)

# --- Auto-refresh ---
st.sidebar.markdown("### ⚙️ Settings")
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown(f"**Last updated:** {datetime.datetime.now().strftime('%H:%M:%S')}")
st.sidebar.markdown("Data refreshes automatically every **60 seconds**.")
