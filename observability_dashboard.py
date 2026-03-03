"""
observability_dashboard.py — Local Observability Dashboard
Self-contained local telemetry: uses a local SQLite database as the persistent store.
Both apps write events via telemetry_logger.py when run locally.
Dashboard reads from the same SQLite file and shows rich metrics.
Run with: streamlit run observability_dashboard.py
"""
import streamlit as st
import pandas as pd
import datetime
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "telemetry.db")

st.set_page_config(
    page_title="📡 Observability Dashboard",
    page_icon="📡",
    layout="wide"
)

# ─── Dark Pro CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
.stApp { background-color: #0f172a; font-family: 'Inter', sans-serif; }
h1,h2,h3 { color: #e2e8f0 !important; }
p, li { color: #94a3b8 !important; }
section[data-testid="stSidebar"] { background: #1e293b; }
section[data-testid="stSidebar"] label { color: #94a3b8 !important; }
div[data-testid="metric-container"] {
    background: linear-gradient(135deg, #1e293b, #0f172a);
    padding: 16px 20px; border-radius: 12px;
    border-left: 4px solid #3b82f6;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}
div[data-testid="metric-container"] > label { color: #94a3b8 !important; font-size: 0.8em; }
div[data-testid="metric-container"] > div { color: #60a5fa !important; font-size: 1.6em; font-weight: 700; }
.stTabs [aria-selected="true"] { color: #60a5fa !important; border-bottom: 2px solid #3b82f6; }
</style>
""", unsafe_allow_html=True)

# ─── DB helpers ────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS llm_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT, model TEXT, query_type TEXT,
            user_query TEXT, response_preview TEXT,
            input_tokens INTEGER, output_tokens INTEGER,
            cost_usd REAL, latency_ms REAL,
            timestamp TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sarvam_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT, audio_source TEXT,
            audio_duration_sec REAL, cost_usd REAL,
            latency_ms REAL, language_code TEXT, num_chunks INTEGER,
            timestamp TEXT
        )
    """)
    conn.commit()
    return conn


@st.cache_data(ttl=10)
def load_llm_events(start: str, end: str, app: str):
    conn = get_db()
    q = "SELECT * FROM llm_events WHERE date(timestamp) BETWEEN ? AND ?"
    params = [start, end]
    if app != "All":
        q += " AND app_name = ?"
        params.append(app)
    q += " ORDER BY timestamp DESC"
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()
    return df


@st.cache_data(ttl=10)
def load_sarvam_events(start: str, end: str, app: str):
    conn = get_db()
    q = "SELECT * FROM sarvam_events WHERE date(timestamp) BETWEEN ? AND ?"
    params = [start, end]
    if app != "All":
        q += " AND app_name = ?"
        params.append(app)
    q += " ORDER BY timestamp DESC"
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()
    return df


def get_distinct_apps():
    conn = get_db()
    apps = [r[0] for r in conn.execute(
        "SELECT DISTINCT app_name FROM llm_events UNION SELECT DISTINCT app_name FROM sarvam_events"
    ).fetchall() if r[0]]
    conn.close()
    return apps

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Filters")
    st.markdown("---")

    today = datetime.date.today()
    start_date = st.date_input("From", value=today - datetime.timedelta(days=30))
    end_date   = st.date_input("To",   value=today)

    all_apps = get_distinct_apps()
    app_options = ["All"] + all_apps
    selected_app = st.selectbox("App", app_options)

    st.markdown("---")
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("**🗄️ DB Location**")
    st.code(DB_PATH, language=None)
    st.caption("Both apps write here when run locally.")

# ─── Load data ─────────────────────────────────────────────────────────────────
llm_df = load_llm_events(str(start_date), str(end_date), selected_app)
sarv_df = load_sarvam_events(str(start_date), str(end_date), selected_app)

# ─── Header ────────────────────────────────────────────────────────────────────
st.title("📡 API Observability Dashboard")
st.markdown(f"Showing data from **{start_date}** → **{end_date}** · App: **{selected_app}**")
st.markdown("---")

# ─── Top Metrics ───────────────────────────────────────────────────────────────
total_llm_cost   = llm_df["cost_usd"].sum()   if not llm_df.empty else 0
total_sarv_cost  = sarv_df["cost_usd"].sum()  if not sarv_df.empty else 0
total_cost       = total_llm_cost + total_sarv_cost
total_llm_calls  = len(llm_df)
total_sarv_calls = len(sarv_df)
total_tokens     = int((llm_df["input_tokens"].sum() + llm_df["output_tokens"].sum())) if not llm_df.empty else 0
avg_latency      = round(llm_df["latency_ms"].mean(), 0) if not llm_df.empty else 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("💰 Total Cost", f"${total_cost:.4f}")
c2.metric("🤖 OpenAI Cost", f"${total_llm_cost:.4f}")
c3.metric("🎙️ Sarvam Cost", f"${total_sarv_cost:.4f}")
c4.metric("📞 LLM Requests", f"{total_llm_calls:,}")
c5.metric("🔤 Tokens Used", f"{total_tokens:,}")
c6.metric("⚡ Avg Latency", f"{avg_latency:.0f}ms")

st.markdown("---")

# ─── Tabs ──────────────────────────────────────────────────────────────────────
t1, t2, t3, t4, t5 = st.tabs([
    "📅 Daily Breakdown", "🤖 OpenAI Detail",
    "🎙️ Sarvam Detail", "🔍 Full Trace Log", "📱 Per-App"
])

# ── Tab 1: Daily ──────────────────────────────────────────────────────────────
with t1:
    if llm_df.empty and sarv_df.empty:
        st.info("No data yet. Use the apps locally to generate telemetry.")
    else:
        if not llm_df.empty:
            llm_df["date"] = pd.to_datetime(llm_df["timestamp"]).dt.date.astype(str)
            daily_llm = llm_df.groupby("date").agg(
                LLM_Calls=("id","count"),
                OpenAI_Cost=("cost_usd","sum"),
                Input_Tokens=("input_tokens","sum"),
                Output_Tokens=("output_tokens","sum"),
                Avg_Latency_ms=("latency_ms","mean"),
            ).reset_index()

        if not sarv_df.empty:
            sarv_df["date"] = pd.to_datetime(sarv_df["timestamp"]).dt.date.astype(str)
            daily_sarv = sarv_df.groupby("date").agg(
                Sarvam_Calls=("id","count"),
                Sarvam_Cost=("cost_usd","sum"),
                Audio_Min=("audio_duration_sec","sum"),
            ).reset_index()
            daily_sarv["Audio_Min"] = (daily_sarv["Audio_Min"] / 60).round(2)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("💰 Daily Cost")
            if not llm_df.empty:
                cost_data = daily_llm[["date","OpenAI_Cost"]].copy()
                if not sarv_df.empty:
                    cost_data = cost_data.merge(daily_sarv[["date","Sarvam_Cost"]], on="date", how="outer").fillna(0)
                st.area_chart(cost_data.set_index("date"))

        with col2:
            st.subheader("📞 Daily Requests")
            if not llm_df.empty:
                req_data = daily_llm[["date","LLM_Calls"]].copy()
                if not sarv_df.empty:
                    req_data = req_data.merge(daily_sarv[["date","Sarvam_Calls"]], on="date", how="outer").fillna(0)
                st.bar_chart(req_data.set_index("date"))

        if not llm_df.empty:
            st.subheader("🔤 Daily Token Usage")
            st.area_chart(daily_llm[["date","Input_Tokens","Output_Tokens"]].set_index("date"))

# ── Tab 2: OpenAI Detail ───────────────────────────────────────────────────────
with t2:
    if llm_df.empty:
        st.info("No OpenAI events logged yet.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("By Model")
            model_stats = llm_df.groupby("model").agg(
                Calls=("id","count"),
                Input_Tokens=("input_tokens","sum"),
                Output_Tokens=("output_tokens","sum"),
                Cost_USD=("cost_usd","sum"),
                Avg_Latency_ms=("latency_ms","mean"),
            ).reset_index()
            model_stats["Cost_USD"] = model_stats["Cost_USD"].round(6)
            model_stats["Avg_Latency_ms"] = model_stats["Avg_Latency_ms"].round(1)
            st.dataframe(model_stats, use_container_width=True)
            st.bar_chart(model_stats.set_index("model")["Cost_USD"])

        with col2:
            st.subheader("By Query Type")
            qt_stats = llm_df.groupby("query_type").agg(
                Calls=("id","count"),
                Cost_USD=("cost_usd","sum"),
                Avg_Latency_ms=("latency_ms","mean"),
            ).reset_index()
            st.dataframe(qt_stats, use_container_width=True)
            st.bar_chart(qt_stats.set_index("query_type")["Calls"])

# ── Tab 3: Sarvam Detail ───────────────────────────────────────────────────────
with t3:
    if sarv_df.empty:
        st.info("No Sarvam events logged yet.")
    else:
        s1, s2, s3 = st.columns(3)
        total_audio_min = sarv_df["audio_duration_sec"].sum() / 60
        s1.metric("📼 Total Audio Processed", f"{total_audio_min:.1f} min")
        s2.metric("🔢 Total Chunks", f"{int(sarv_df['num_chunks'].sum())}")
        s3.metric("💲 Total Sarvam Cost", f"${sarv_df['cost_usd'].sum():.4f}")

        st.subheader("Transcription Events")
        display_cols = ["timestamp","app_name","audio_source","audio_duration_sec","num_chunks","language_code","cost_usd","latency_ms"]
        st.dataframe(sarv_df[[c for c in display_cols if c in sarv_df.columns]], use_container_width=True)

# ── Tab 4: Trace Log ──────────────────────────────────────────────────────────
with t4:
    if llm_df.empty:
        st.info("No traces yet.")
    else:
        st.subheader(f"🔍 {len(llm_df)} LLM Trace(s)")
        trace_cols = ["timestamp","app_name","query_type","user_query","response_preview",
                      "model","input_tokens","output_tokens","cost_usd","latency_ms"]
        st.dataframe(llm_df[[c for c in trace_cols if c in llm_df.columns]], use_container_width=True)

# ── Tab 5: Per App ─────────────────────────────────────────────────────────────
with t5:
    if llm_df.empty:
        st.info("No data.")
    else:
        app_stats = llm_df.groupby("app_name").agg(
            LLM_Calls=("id","count"),
            Total_Cost_USD=("cost_usd","sum"),
            Input_Tokens=("input_tokens","sum"),
            Output_Tokens=("output_tokens","sum"),
            Avg_Latency_ms=("latency_ms","mean"),
        ).reset_index()
        app_stats["Total_Cost_USD"] = app_stats["Total_Cost_USD"].round(6)
        app_stats["Avg_Latency_ms"] = app_stats["Avg_Latency_ms"].round(1)
        st.dataframe(app_stats, use_container_width=True)

        if not sarv_df.empty:
            sarv_app = sarv_df.groupby("app_name").agg(
                Calls=("id","count"),
                Audio_Min=("audio_duration_sec","sum"),
                Sarvam_Cost=("cost_usd","sum"),
            ).reset_index()
            sarv_app["Audio_Min"] = (sarv_app["Audio_Min"] / 60).round(2)
            st.subheader("Sarvam by App")
            st.dataframe(sarv_app, use_container_width=True)

st.caption(f"DB: `{DB_PATH}` · Last refreshed: {datetime.datetime.now().strftime('%H:%M:%S')}")
