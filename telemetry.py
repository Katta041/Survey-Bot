"""
telemetry.py — Shared Observability Module for Streamlit Apps
Uses Google Sheets as a persistent telemetry sink.
Follows OpenTelemetry-compatible patterns: trace_id, span_id, timestamps, latency.
"""

import uuid
import time
import datetime
import json
import threading
import streamlit as st

# ── Cost table (USD per 1M tokens) ─────────────────────────────────────────
COST_TABLE = {
    "gpt-4o":       {"input": 2.50,  "output": 10.00},
    "gpt-4o-mini":  {"input": 0.15,  "output": 0.60},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}

SARVAM_COST_PER_MIN = 0.005  # Approx USD per minute of audio transcribed

# ── Google Sheets client (lazy init) ───────────────────────────────────────
_sheet_client = None
_sheet_lock = threading.Lock()


def _get_sheet():
    """Returns the Google Sheets worksheet, initialised lazily per process."""
    global _sheet_client
    with _sheet_lock:
        if _sheet_client is not None:
            return _sheet_client
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            # Load credentials from Streamlit secrets or local config
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
                return None

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            creds = Credentials.from_service_account_info(sa_json, scopes=scopes)
            gc = gspread.authorize(creds)
            spreadsheet = gc.open_by_key(sheets_id)

            # Ensure worksheets exist
            worksheets = {ws.title for ws in spreadsheet.worksheets()}
            for sheet_name, headers in [
                ("llm_traces", [
                    "trace_id", "span_id", "app_name", "timestamp_utc",
                    "user_query", "response_preview", "model",
                    "input_tokens", "output_tokens", "cost_usd",
                    "latency_ms", "query_type",
                ]),
                ("sarvam_traces", [
                    "trace_id", "span_id", "app_name", "timestamp_utc",
                    "audio_source", "audio_duration_sec",
                    "cost_usd", "latency_ms", "language_code", "num_chunks",
                ]),
                ("daily_summary", [
                    "date", "app_name", "llm_calls", "sarvam_calls",
                    "total_input_tokens", "total_output_tokens",
                    "total_cost_usd", "avg_latency_ms",
                ]),
            ]:
                if sheet_name not in worksheets:
                    ws = spreadsheet.add_worksheet(title=sheet_name, rows=5000, cols=20)
                    ws.append_row(headers)

            # Cache worksheet references
            _sheet_client = {
                "llm": spreadsheet.worksheet("llm_traces"),
                "sarvam": spreadsheet.worksheet("sarvam_traces"),
                "daily": spreadsheet.worksheet("daily_summary"),
            }
            return _sheet_client
        except Exception as e:
            print(f"[telemetry] Could not connect to Google Sheets: {e}")
            return None


# ── Public helpers ─────────────────────────────────────────────────────────

def new_trace_id() -> str:
    """Generate a globally unique trace ID (OTel-compatible hex string)."""
    return uuid.uuid4().hex


def new_span_id() -> str:
    """Generate a span ID within a trace."""
    return uuid.uuid4().hex[:16]


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate API cost in USD."""
    rates = COST_TABLE.get(model, {"input": 0, "output": 0})
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000


def log_llm_call(
    *,
    app_name: str,
    trace_id: str,
    user_query: str,
    response: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
    query_type: str = "general",
):
    """Log an LLM call event to Google Sheets asynchronously."""
    span_id = new_span_id()
    cost = estimate_cost(model, input_tokens, output_tokens)
    row = [
        trace_id,
        span_id,
        app_name,
        datetime.datetime.utcnow().isoformat(),
        user_query[:500],
        response[:300] if response else "",
        model,
        input_tokens,
        output_tokens,
        round(cost, 6),
        round(latency_ms, 1),
        query_type,
    ]
    _async_append("llm", row)


def log_sarvam_call(
    *,
    app_name: str,
    trace_id: str,
    audio_source: str,
    audio_duration_sec: float,
    latency_ms: float,
    language_code: str = "ta-IN",
    num_chunks: int = 1,
):
    """Log a Sarvam transcription event to Google Sheets asynchronously."""
    span_id = new_span_id()
    cost = round((audio_duration_sec / 60) * SARVAM_COST_PER_MIN, 6)
    row = [
        trace_id,
        span_id,
        app_name,
        datetime.datetime.utcnow().isoformat(),
        audio_source[:300],
        round(audio_duration_sec, 1),
        cost,
        round(latency_ms, 1),
        language_code,
        num_chunks,
    ]
    _async_append("sarvam", row)


def _async_append(sheet_key: str, row: list):
    """Append a row to Google Sheets in a background thread — non-blocking."""
    def _write():
        try:
            sheets = _get_sheet()
            if sheets:
                sheets[sheet_key].append_row(row, value_input_option="RAW")
        except Exception as e:
            print(f"[telemetry] Write error: {e}")
    threading.Thread(target=_write, daemon=True).start()


# ── Context manager for timing spans ──────────────────────────────────────

class Span:
    """Lightweight context manager that measures latency of a block."""
    def __init__(self):
        self.latency_ms = 0.0
        self._start = None

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_):
        self.latency_ms = (time.perf_counter() - self._start) * 1000
