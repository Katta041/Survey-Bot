"""
observability_dashboard.py — Enterprise Observability Dashboard
Clean, Datadog-style UI. Reads from local SQLite telemetry DB.
Run: streamlit run observability_dashboard.py
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import datetime
import sqlite3
import os
import sys
from pathlib import Path

# Add project root to path for modular imports
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.core.config import Config

DB_PATH = Config.TELEMETRY_DB_PATH

st.set_page_config(
    page_title="Observability · API Intelligence",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════
#  GLOBAL CSS — Enterprise Dark Theme
# ══════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Root ──────────────────────────────────── */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #0b0f19; }

/* ── Sidebar ───────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #111827;
    border-right: 1px solid #1f2937;
}
section[data-testid="stSidebar"] * { color: #9ca3af !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2 { color: #f9fafb !important; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stDateInput label { color: #6b7280 !important; font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 0.05em; }

/* ── Titles ────────────────────────────────── */
h1 { font-size: 1.6rem !important; font-weight: 700 !important; color: #f9fafb !important; letter-spacing: -0.025em; }
h2 { font-size: 1.1rem !important; font-weight: 600 !important; color: #e5e7eb !important; }
h3 { font-size: 0.9rem !important; font-weight: 500 !important; color: #9ca3af !important; text-transform: uppercase; letter-spacing: 0.08em; }

/* ── KPI Cards ─────────────────────────────── */
.kpi-card {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 20px 24px;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
}
.kpi-card.blue::before  { background: linear-gradient(90deg, #3b82f6, #6366f1); }
.kpi-card.green::before { background: linear-gradient(90deg, #10b981, #34d399); }
.kpi-card.amber::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.kpi-card.rose::before  { background: linear-gradient(90deg, #f43f5e, #fb7185); }
.kpi-card.purple::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.kpi-card.cyan::before  { background: linear-gradient(90deg, #06b6d4, #22d3ee); }

.kpi-label { font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; color: #6b7280; margin-bottom: 10px; }
.kpi-value { font-size: 2rem; font-weight: 700; color: #f9fafb; line-height: 1; }
.kpi-sub   { font-size: 0.75rem; color: #4b5563; margin-top: 8px; }

/* ── Section headers ───────────────────────── */
.section-label {
    display: flex; align-items: center; gap: 8px;
    font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.12em; color: #4b5563;
    border-bottom: 1px solid #1f2937;
    padding-bottom: 10px; margin: 28px 0 18px 0;
}

/* ── Table ─────────────────────────────────── */
.stDataFrame { border-radius: 10px !important; border: 1px solid #1f2937 !important; }
.stDataFrame thead { background: #1f2937; }

/* ── Tabs ──────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: #111827 !important;
    border-bottom: 1px solid #1f2937 !important;
    border-radius: 8px 8px 0 0;
    gap: 0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #6b7280 !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    padding: 10px 20px !important;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    color: #f9fafb !important;
    background: #1f2937 !important;
    border-bottom: 2px solid #3b82f6 !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: #111827;
    border: 1px solid #1f2937;
    border-top: none;
    border-radius: 0 0 8px 8px;
    padding: 20px;
}

/* ── Alerts / info boxes ───────────────────── */
.stAlert { border-radius: 8px !important; border: 1px solid #1f2937 !important; }

/* ── Buttons ───────────────────────────────── */
.stButton button {
    background: #1f2937 !important;
    color: #d1d5db !important;
    border: 1px solid #374151 !important;
    border-radius: 8px !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    transition: all 0.15s;
}
.stButton button:hover {
    background: #374151 !important;
    color: #f9fafb !important;
    border-color: #4b5563 !important;
}

/* ── Caption / footer ──────────────────────── */
.footer-bar {
    border-top: 1px solid #1f2937;
    padding-top: 12px; margin-top: 32px;
    font-size: 0.7rem; color: #374151;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  PLOTLY THEME
# ══════════════════════════════════════════════
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#9ca3af", size=11),
    margin=dict(l=0, r=0, t=20, b=0),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#9ca3af")),
    xaxis=dict(gridcolor="#1f2937", linecolor="#1f2937", showgrid=True, zeroline=False),
    yaxis=dict(gridcolor="#1f2937", linecolor="#1f2937", showgrid=True, zeroline=False),
)
COLORS = ["#3b82f6","#10b981","#f59e0b","#8b5cf6","#f43f5e","#06b6d4"]

# ══════════════════════════════════════════════
#  DB HELPERS / API CLIENT
# ══════════════════════════════════════════════
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS llm_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, app_name TEXT, model TEXT, query_type TEXT,
        user_query TEXT, response_preview TEXT, input_tokens INTEGER, output_tokens INTEGER,
        cost_usd REAL, latency_ms REAL, timestamp TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS sarvam_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, app_name TEXT, audio_source TEXT,
        audio_duration_sec REAL, cost_usd REAL, latency_ms REAL,
        language_code TEXT, num_chunks INTEGER, timestamp TEXT)""")
    conn.commit()
    return conn

def _fetch_api(endpoint: str, params: dict = None):
    api_url = os.getenv("TELEMETRY_API_URL")
    api_key = os.getenv("TELEMETRY_API_KEY")
    
    if not api_url:
        try:
            api_url = st.secrets.get("TELEMETRY_API_URL")
            api_key = st.secrets.get("TELEMETRY_API_KEY", "dev-secret-key-123")
        except Exception:
            pass
            
    api_key = api_key or "dev-secret-key-123"
    
    if not api_url:
        return None
        
    import requests
    try:
        r = requests.get(f"{api_url.rstrip('/')}{endpoint}", params=params, headers={"Authorization": f"Bearer {api_key}"}, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"Failed to fetch {endpoint} via proxy: {e}")
        return None

@st.cache_data(ttl=15)
def load_llm(start, end, app):
    df = pd.DataFrame()
    if os.getenv("TELEMETRY_API_URL"):
        data = _fetch_api("/api/telemetry/llm", {"start": start, "end": end, "app": app})
        if data is not None:
            df = pd.DataFrame(data)
    else:
        conn = get_db()
        q = "SELECT * FROM llm_events WHERE date(timestamp) BETWEEN ? AND ?"
        p = [start, end]
        if app != "All":
            q += " AND app_name=?"; p.append(app)
        df = pd.read_sql_query(q+" ORDER BY timestamp DESC", conn, params=p)
        conn.close()
        
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["date"] = df["timestamp"].dt.date
        for c in ["input_tokens","output_tokens","cost_usd","latency_ms"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

@st.cache_data(ttl=15)
def load_sarvam(start, end, app):
    df = pd.DataFrame()
    if os.getenv("TELEMETRY_API_URL"):
        data = _fetch_api("/api/telemetry/sarvam", {"start": start, "end": end, "app": app})
        if data is not None:
            df = pd.DataFrame(data)
    else:
        conn = get_db()
        q = "SELECT * FROM sarvam_events WHERE date(timestamp) BETWEEN ? AND ?"
        p = [start, end]
        if app != "All":
            q += " AND app_name=?"; p.append(app)
        df = pd.read_sql_query(q+" ORDER BY timestamp DESC", conn, params=p)
        conn.close()
        
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["date"] = df["timestamp"].dt.date
        for c in ["audio_duration_sec","cost_usd","latency_ms"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

def app_list():
    if os.getenv("TELEMETRY_API_URL"):
        data = _fetch_api("/api/telemetry/apps")
        return data if data else []
        
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT app_name FROM llm_events UNION SELECT DISTINCT app_name FROM sarvam_events").fetchall()
    conn.close()
    return [r[0] for r in rows if r[0]]

# ══════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 📡 Observability")
    st.markdown("<div style='height:1px;background:#1f2937;margin:12px 0 20px'></div>", unsafe_allow_html=True)

    today = datetime.date.today()
    quick = st.selectbox("Quick range", ["Last 7 days","Last 30 days","Today","Custom"], index=1)
    if quick == "Today":
        start_date, end_date = today, today
    elif quick == "Last 7 days":
        start_date, end_date = today - datetime.timedelta(7), today
    elif quick == "Last 30 days":
        start_date, end_date = today - datetime.timedelta(30), today
    else:
        start_date = st.date_input("From", value=today - datetime.timedelta(30))
        end_date   = st.date_input("To",   value=today)

    apps = ["All"] + app_list()
    selected_app = st.selectbox("Application", apps)

    st.markdown("<div style='height:1px;background:#1f2937;margin:20px 0'></div>", unsafe_allow_html=True)

    if st.button("↺  Refresh", width='stretch'):
        st.cache_data.clear()
        st.rerun()

    st.markdown("<div style='height:1px;background:#1f2937;margin:20px 0'></div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.65rem;color:#374151'>DB · <code style='color:#4b5563'>{DB_PATH.name}</code></div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.65rem;color:#374151;margin-top:4px'>Updated · {datetime.datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  LOAD DATA
# ══════════════════════════════════════════════
llm = load_llm(str(start_date), str(end_date), selected_app)
sarv = load_sarvam(str(start_date), str(end_date), selected_app)

# ══════════════════════════════════════════════
#  PAGE HEADER
# ══════════════════════════════════════════════
col_h1, col_h2 = st.columns([3,1])
with col_h1:
    st.markdown(f"<h1>API Intelligence Dashboard</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#4b5563;font-size:0.8rem;margin-top:-8px'>{start_date.strftime('%b %d')} – {end_date.strftime('%b %d, %Y')} &nbsp;·&nbsp; {selected_app}</p>", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  KPI ROW
# ══════════════════════════════════════════════
total_llm_cost  = llm["cost_usd"].sum()   if not llm.empty else 0
total_sarv_cost = sarv["cost_usd"].sum()  if not sarv.empty else 0
total_cost      = total_llm_cost + total_sarv_cost
total_calls     = len(llm)
total_tokens    = int(llm["input_tokens"].sum() + llm["output_tokens"].sum()) if not llm.empty else 0
avg_latency     = llm["latency_ms"].mean() if not llm.empty else 0
sarv_calls      = len(sarv)
audio_min       = sarv["audio_duration_sec"].sum() / 60 if not sarv.empty else 0

k1,k2,k3,k4,k5,k6 = st.columns(6)
cards = [
    (k1,"blue","Total Spend", f"${total_cost:.4f}", f"OpenAI ${total_llm_cost:.4f} · Sarvam ${total_sarv_cost:.4f}"),
    (k2,"green","LLM Calls", f"{total_calls:,}", f"{len(llm['model'].unique()) if not llm.empty else 0} model(s)"),
    (k3,"amber","Tokens Used", f"{total_tokens:,}", f"avg {int(total_tokens/max(total_calls,1)):,} / call"),
    (k4,"rose","Avg Latency", f"{avg_latency:,.0f}ms", f"p50 benchmark < 2000ms"),
    (k5,"purple","Sarvam Transcriptions", f"{sarv_calls}", f"{audio_min:.1f} min audio"),
    (k6,"cyan","Sarvam Cost", f"${total_sarv_cost:.4f}", f"~${0.005:.3f}/min rate"),
]
for col, color, label, val, sub in cards:
    with col:
        st.markdown(f"""
        <div class="kpi-card {color}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{val}</div>
            <div class="kpi-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  MAIN TABS
# ══════════════════════════════════════════════
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
tab_overview, tab_llm, tab_sarvam, tab_traces, tab_apps = st.tabs([
    "  Overview  ", "  OpenAI  ", "  Sarvam  ", "  Traces  ", "  By App  "
])

# ─── OVERVIEW ─────────────────────────────────────────────────────────────────
with tab_overview:
    if llm.empty and sarv.empty:
        st.info("No telemetry data yet. Run either app locally to start capturing events.")
    else:
        r1c1, r1c2 = st.columns(2)

        # Daily cost area chart
        with r1c1:
            st.markdown("##### Daily API Spend (USD)")
            if not llm.empty:
                daily = llm.groupby("date")["cost_usd"].sum().reset_index(name="OpenAI")
                if not sarv.empty:
                    ds = sarv.groupby("date")["cost_usd"].sum().reset_index(name="Sarvam")
                    daily = daily.merge(ds, on="date", how="outer").fillna(0)
                else:
                    daily["Sarvam"] = 0
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=daily["date"].astype(str), y=daily["OpenAI"],
                    fill="tozeroy", name="OpenAI", line=dict(color="#3b82f6", width=2),
                    fillcolor="rgba(59,130,246,0.15)"))
                fig.add_trace(go.Scatter(x=daily["date"].astype(str), y=daily["Sarvam"],
                    fill="tozeroy", name="Sarvam", line=dict(color="#10b981", width=2),
                    fillcolor="rgba(16,185,129,0.15)"))
                fig.update_layout(**PLOTLY_LAYOUT, height=220)
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

        # Daily call volume bars
        with r1c2:
            st.markdown("##### Daily Request Volume")
            if not llm.empty:
                dv = llm.groupby("date")["id"].count().reset_index(name="LLM Calls")
                if not sarv.empty:
                    ds2 = sarv.groupby("date")["id"].count().reset_index(name="Sarvam")
                    dv = dv.merge(ds2, on="date", how="outer").fillna(0)
                else:
                    dv["Sarvam"] = 0
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(x=dv["date"].astype(str), y=dv["LLM Calls"], name="LLM Calls",
                    marker_color="#6366f1", marker_line_width=0))
                fig2.add_trace(go.Bar(x=dv["date"].astype(str), y=dv["Sarvam"], name="Sarvam",
                    marker_color="#10b981", marker_line_width=0))
                fig2.update_layout(**PLOTLY_LAYOUT, barmode="group", height=220)
                st.plotly_chart(fig2, width='stretch', config={"displayModeBar": False})

        r2c1, r2c2 = st.columns(2)
        with r2c1:
            st.markdown("##### Token Consumption")
            if not llm.empty:
                dt = llm.groupby("date")[["input_tokens","output_tokens"]].sum().reset_index()
                fig3 = go.Figure()
                fig3.add_trace(go.Bar(x=dt["date"].astype(str), y=dt["input_tokens"], name="Input",
                    marker_color="#3b82f6", marker_line_width=0))
                fig3.add_trace(go.Bar(x=dt["date"].astype(str), y=dt["output_tokens"], name="Output",
                    marker_color="#8b5cf6", marker_line_width=0))
                fig3.update_layout(**PLOTLY_LAYOUT, barmode="stack", height=220)
                st.plotly_chart(fig3, width='stretch', config={"displayModeBar": False})

        with r2c2:
            st.markdown("##### Cost by Query Type")
            if not llm.empty:
                qt = llm.groupby("query_type")["cost_usd"].sum().reset_index()
                fig4 = go.Figure(go.Pie(
                    labels=qt["query_type"], values=qt["cost_usd"].round(6),
                    hole=0.65,
                    marker=dict(colors=COLORS, line=dict(color="#0b0f19",width=2)),
                    textinfo="label+percent",
                    textfont=dict(color="#9ca3af", size=11),
                ))
                fig4.update_layout(**PLOTLY_LAYOUT, height=220,
                    annotations=[dict(text=f"${qt['cost_usd'].sum():.4f}", x=0.5, y=0.5,
                        font=dict(size=14, color="#f9fafb"), showarrow=False)])
                st.plotly_chart(fig4, width='stretch', config={"displayModeBar": False})

# ─── OpenAI ───────────────────────────────────────────────────────────────────
with tab_llm:
    if llm.empty:
        st.info("No OpenAI events recorded yet.")
    else:
        mc1, mc2 = st.columns(2)
        with mc1:
            st.markdown("##### Cost & Latency by Model")
            ms = llm.groupby("model").agg(
                Requests=("id","count"),
                Avg_Latency_ms=("latency_ms","mean"),
                Cost_USD=("cost_usd","sum"),
            ).reset_index().sort_values("Cost_USD", ascending=False)

            fig = go.Figure()
            fig.add_trace(go.Bar(x=ms["model"], y=ms["Cost_USD"], name="Cost (USD)",
                marker_color="#3b82f6", marker_line_width=0, yaxis="y"))
            fig.add_trace(go.Scatter(x=ms["model"], y=ms["Avg_Latency_ms"], name="Avg Latency (ms)",
                mode="markers+lines", marker=dict(color="#f59e0b", size=8), yaxis="y2"))
            layout_vars = {k: v for k, v in PLOTLY_LAYOUT.items() if k != "yaxis"}
            layout_vars.pop("yaxis", None)
            layout_vars["height"] = 260
            layout_vars["yaxis"] = dict(title="Cost USD", gridcolor="#1f2937", zeroline=False)
            layout_vars["yaxis2"] = dict(title="Latency ms", overlaying="y", side="right", gridcolor="#1f2937", zeroline=False)
            fig.update_layout(**layout_vars)
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

            ms["Cost_USD"] = ms["Cost_USD"].round(6)
            ms["Avg_Latency_ms"] = ms["Avg_Latency_ms"].round(1)
            st.dataframe(ms, hide_index=True, width='stretch')

        with mc2:
            st.markdown("##### Calls by Query Type")
            qt = llm.groupby("query_type").agg(
                Calls=("id","count"),
                Cost_USD=("cost_usd","sum"),
                Avg_Latency_ms=("latency_ms","mean"),
            ).reset_index()
            fig2 = go.Figure(go.Bar(
                x=qt["Calls"], y=qt["query_type"],
                orientation="h",
                marker=dict(color=COLORS[:len(qt)], line_width=0),
                text=qt["Calls"], textposition="outside",
                textfont=dict(color="#9ca3af"),
            ))
            fig2.update_layout(**PLOTLY_LAYOUT, height=200)
            st.plotly_chart(fig2, width='stretch', config={"displayModeBar": False})

            st.markdown("##### Top Questions Asked")
            top_q = llm[["timestamp","query_type","user_query","cost_usd","latency_ms"]].head(10)
            top_q["timestamp"] = top_q["timestamp"].dt.strftime("%m/%d %H:%M")
            top_q["cost_usd"] = top_q["cost_usd"].round(6)
            top_q["latency_ms"] = top_q["latency_ms"].round(0).astype(int)
            st.dataframe(top_q, hide_index=True, width='stretch')

# ─── Sarvam ───────────────────────────────────────────────────────────────────
with tab_sarvam:
    if sarv.empty:
        st.info("No Sarvam transcription events yet. Run the Audio Insight Engine locally.")
    else:
        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown("##### Audio Duration Processed (per day)")
            ds = sarv.copy()
            ds["audio_min"] = ds["audio_duration_sec"] / 60
            dg = ds.groupby("date")["audio_min"].sum().reset_index()
            fig = go.Figure(go.Bar(
                x=dg["date"].astype(str), y=dg["audio_min"].round(2),
                marker_color="#10b981", marker_line_width=0,
            ))
            fig.update_layout(**PLOTLY_LAYOUT, height=220,
                yaxis_title="Minutes")
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

        with sc2:
            st.markdown("##### Chunks Distribution")
            fig2 = go.Figure(go.Box(
                y=sarv["num_chunks"], name="Chunks per call",
                marker_color="#8b5cf6", line_color="#8b5cf6",
                fillcolor="rgba(139,92,246,0.15)",
            ))
            fig2.update_layout(**PLOTLY_LAYOUT, height=220)
            st.plotly_chart(fig2, width='stretch', config={"displayModeBar": False})

        st.markdown("##### Transcription Event Log")
        show = sarv[["timestamp","app_name","audio_source","audio_duration_sec","num_chunks","language_code","cost_usd","latency_ms"]].copy()
        show["timestamp"] = show["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        show["audio_duration_sec"] = show["audio_duration_sec"].round(1)
        show["cost_usd"] = show["cost_usd"].round(6)
        show["latency_ms"] = show["latency_ms"].round(0).astype(int)
        st.dataframe(show, hide_index=True, width='stretch')

# ─── Traces ───────────────────────────────────────────────────────────────────
with tab_traces:
    if llm.empty:
        st.info("No traces yet.")
    else:
        # Latency distribution
        fig = go.Figure(go.Histogram(
            x=llm["latency_ms"], nbinsx=20,
            marker_color="#3b82f6", marker_line_width=0,
            opacity=0.85,
        ))
        fig.update_layout(**PLOTLY_LAYOUT, height=180,
            xaxis_title="Latency (ms)", yaxis_title="Count",
            title=dict(text="Latency Distribution", font=dict(color="#9ca3af", size=11)))
        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

        st.markdown("##### Full LLM Trace Log")
        trace_show = llm[["timestamp","app_name","query_type","user_query","response_preview",
                           "model","input_tokens","output_tokens","cost_usd","latency_ms"]].copy()
        trace_show["timestamp"]   = trace_show["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        trace_show["cost_usd"]    = trace_show["cost_usd"].round(6)
        trace_show["latency_ms"]  = trace_show["latency_ms"].round(0).astype(int)
        st.dataframe(trace_show, hide_index=True, width='stretch', height=420)

# ─── By App ───────────────────────────────────────────────────────────────────
with tab_apps:
    if llm.empty:
        st.info("No data.")
    else:
        app_stats = llm.groupby("app_name").agg(
            LLM_Calls=("id","count"),
            Cost_USD=("cost_usd","sum"),
            Input_Tokens=("input_tokens","sum"),
            Output_Tokens=("output_tokens","sum"),
            Avg_Latency_ms=("latency_ms","mean"),
        ).reset_index()

        fig = go.Figure()
        fig.add_trace(go.Bar(x=app_stats["app_name"], y=app_stats["LLM_Calls"],
            name="LLM Calls", marker_color="#3b82f6", marker_line_width=0))
        if not sarv.empty:
            sa = sarv.groupby("app_name")["id"].count().reset_index(name="Sarvam_Calls")
            app_stats = app_stats.merge(sa, on="app_name", how="left").fillna(0)
            fig.add_trace(go.Bar(x=app_stats["app_name"], y=app_stats["Sarvam_Calls"],
                name="Sarvam Calls", marker_color="#10b981", marker_line_width=0))

        fig.update_layout(**PLOTLY_LAYOUT, barmode="group", height=220,
            title=dict(text="Requests per App", font=dict(color="#9ca3af",size=11)))
        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

        app_stats["Cost_USD"] = app_stats["Cost_USD"].round(6)
        app_stats["Avg_Latency_ms"] = app_stats["Avg_Latency_ms"].round(1)
        st.dataframe(app_stats, hide_index=True, width='stretch')

        # App reference cards
        st.markdown("<div class='section-label'>Deployed Apps</div>", unsafe_allow_html=True)
        a1, a2 = st.columns(2)
        with a1:
            st.markdown("""<div class="kpi-card blue" style="padding:16px 20px">
                <div class="kpi-label">🎙️ Audio Insight Engine</div>
                <div style="font-size:0.8rem;color:#6b7280;margin-top:8px">
                survey-bot-crx465aaxrusnn5pjtxh8h.streamlit.app<br>
                <code style="color:#4b5563">gpt-4o</code> · <code style="color:#4b5563">Sarvam saaras:v3</code>
                </div></div>""", unsafe_allow_html=True)
        with a2:
            st.markdown("""<div class="kpi-card purple" style="padding:16px 20px">
                <div class="kpi-label">🗳️ Survey Chatbot TN</div>
                <div style="font-size:0.8rem;color:#6b7280;margin-top:8px">
                app-app-kxsuhapap3cjihqm2szeb8.streamlit.app<br>
                <code style="color:#4b5563">gpt-4o</code> · decision + synthesis + formatting
                </div></div>""", unsafe_allow_html=True)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="footer-bar">
  📡 API Intelligence Dashboard &nbsp;·&nbsp; DB: <code>{DB_PATH.name}</code>
  &nbsp;·&nbsp; {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST
  &nbsp;·&nbsp; Auto-refresh every 15s
</div>""", unsafe_allow_html=True)
