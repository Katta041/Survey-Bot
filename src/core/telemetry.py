"""
telemetry.py — Lightweight local telemetry module.
Writes LLM and Sarvam call events to a local SQLite database.
The observability_dashboard.py reads from this same DB.
Non-blocking: all writes happen in background threads.
"""
import uuid
import time
import datetime
import threading
import sqlite3
import os
import sys
from pathlib import Path

# Add project root to path to allow absolute imports when running as scripts
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.core.config import Config

DB_PATH = Config.TELEMETRY_DB_PATH

# ── Cost table (USD per 1M tokens) ────────────────────────────────────────────
COST_TABLE = {
    "gpt-4o":        {"input": 2.50,  "output": 10.00},
    "gpt-4o-mini":   {"input": 0.15,  "output": 0.60},
    "gpt-4-turbo":   {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50,  "output": 1.50},
}
SARVAM_COST_PER_MIN = 0.005  # USD per minute of audio

# ── DB init ────────────────────────────────────────────────────────────────────
def _ensure_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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
    conn.close()

_ensure_db()

# ── Helpers ────────────────────────────────────────────────────────────────────
def new_trace_id() -> str:
    return uuid.uuid4().hex

def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = COST_TABLE.get(model, {"input": 2.50, "output": 10.00})
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000

# ── Public logging functions ───────────────────────────────────────────────────
def _send_to_api_or_db(endpoint: str, payload: dict, sql: str, params: tuple):
    api_url = os.getenv("TELEMETRY_API_URL")
    api_key = os.getenv("TELEMETRY_API_KEY")
    
    if not api_url:
        try:
            import streamlit as st
            api_url = str(st.secrets.get("TELEMETRY_API_URL", ""))
            api_key = str(st.secrets.get("TELEMETRY_API_KEY", ""))
        except Exception as e:
            print(f"[telemetry] Secrets fallback error: {e}")
            
    api_url = api_url.strip() if api_url else ""
    api_key = api_key.strip() if api_key else "dev-secret-key-123"
    
    if api_url and api_url.startswith("http"):
        import requests
        try:
            # print(f"[telemetry] Sending POST to {api_url.rstrip('/')}{endpoint}")
            requests.post(
                f"{api_url.rstrip('/')}{endpoint}",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=5
            )
        except Exception as e:
            print(f"[telemetry] API send error: {e}")
    else:
        # print(f"[telemetry] No valid API URL found (val: {api_url}), falling back to SQLite")
        _async_write(sql, params)

def log_llm_call(
    *,
    app_name: str,
    trace_id: str = "",
    user_query: str = "",
    response: str = "",
    model: str = "gpt-4o",
    input_tokens: int = 0,
    output_tokens: int = 0,
    latency_ms: float = 0.0,
    query_type: str = "general",
):
    cost = estimate_cost(model, input_tokens, output_tokens)
    ts = datetime.datetime.utcnow().isoformat()
    row = (
        app_name, model, query_type, user_query[:500], response[:300],
        input_tokens, output_tokens, round(cost, 8), round(latency_ms, 1), ts
    )
    
    payload = {
        "app_name": app_name, "model": model, "query_type": query_type,
        "user_query": user_query[:500], "response_preview": response[:300],
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "cost_usd": round(cost, 8), "latency_ms": round(latency_ms, 1), "timestamp": ts
    }
    
    sql = ("INSERT INTO llm_events "
           "(app_name, model, query_type, user_query, response_preview, "
           "input_tokens, output_tokens, cost_usd, latency_ms, timestamp) "
           "VALUES (?,?,?,?,?,?,?,?,?,?)")
    _send_to_api_or_db("/api/telemetry/llm", payload, sql, row)


def log_sarvam_call(
    *,
    app_name: str,
    trace_id: str = "",
    audio_source: str = "uploaded_file",
    audio_duration_sec: float = 0.0,
    latency_ms: float = 0.0,
    language_code: str = "ta-IN",
    num_chunks: int = 1,
):
    cost = round((audio_duration_sec / 60) * SARVAM_COST_PER_MIN, 8)
    ts = datetime.datetime.utcnow().isoformat()
    row = (
        app_name, audio_source, round(audio_duration_sec, 2), cost,
        round(latency_ms, 1), language_code, num_chunks, ts
    )
    
    payload = {
        "app_name": app_name, "audio_source": audio_source, 
        "audio_duration_sec": round(audio_duration_sec, 2), "cost_usd": cost,
        "latency_ms": round(latency_ms, 1), "language_code": language_code, 
        "num_chunks": num_chunks, "timestamp": ts
    }
    
    sql = ("INSERT INTO sarvam_events "
           "(app_name, audio_source, audio_duration_sec, cost_usd, "
           "latency_ms, language_code, num_chunks, timestamp) "
           "VALUES (?,?,?,?,?,?,?,?)")
    _send_to_api_or_db("/api/telemetry/sarvam", payload, sql, row)


def _async_write(sql: str, params: tuple):
    def _run():
        try:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            conn.execute(sql, params)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[telemetry] DB write error: {e}")
    threading.Thread(target=_run, daemon=True).start()


# ── Span: context manager for timing code blocks ──────────────────────────────
class Span:
    def __init__(self):
        self.latency_ms = 0.0
        self._start = None

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_):
        self.latency_ms = (time.perf_counter() - self._start) * 1000
