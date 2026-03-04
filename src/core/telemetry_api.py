import os
import sqlite3
import pandas as pd
from flask import Flask, request, jsonify
from pathlib import Path
from src.core.config import Config

app = Flask(__name__)
DB_PATH = Config.TELEMETRY_DB_PATH
API_KEY = os.getenv("TELEMETRY_API_KEY", "dev-secret-key-123")

def require_api_key(func):
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or auth_header != f"Bearer {API_KEY}":
            return jsonify({"error": "Unauthorized"}), 401
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    # Ensure tables exist just in case
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

@app.route("/api/telemetry/llm", methods=["POST"])
@require_api_key
def add_llm_event():
    data = request.json
    try:
        conn = get_db()
        row = (
            data.get("app_name"), data.get("model"), data.get("query_type"),
            data.get("user_query"), data.get("response_preview"),
            data.get("input_tokens"), data.get("output_tokens"),
            data.get("cost_usd"), data.get("latency_ms"), data.get("timestamp")
        )
        conn.execute("INSERT INTO llm_events (app_name, model, query_type, user_query, response_preview, input_tokens, output_tokens, cost_usd, latency_ms, timestamp) VALUES (?,?,?,?,?,?,?,?,?,?)", row)
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/telemetry/sarvam", methods=["POST"])
@require_api_key
def add_sarvam_event():
    data = request.json
    try:
        conn = get_db()
        row = (
            data.get("app_name"), data.get("audio_source"), data.get("audio_duration_sec"),
            data.get("cost_usd"), data.get("latency_ms"), data.get("language_code"),
            data.get("num_chunks"), data.get("timestamp")
        )
        conn.execute("INSERT INTO sarvam_events (app_name, audio_source, audio_duration_sec, cost_usd, latency_ms, language_code, num_chunks, timestamp) VALUES (?,?,?,?,?,?,?,?)", row)
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/telemetry/llm", methods=["GET"])
@require_api_key
def get_llm_events():
    start = request.args.get("start")
    end = request.args.get("end")
    app_name = request.args.get("app")
    
    conn = get_db()
    q = "SELECT * FROM llm_events WHERE date(timestamp) BETWEEN ? AND ?"
    p = [start, end]
    if app_name and app_name != "All":
        q += " AND app_name=?"
        p.append(app_name)
    df = pd.read_sql_query(q + " ORDER BY timestamp DESC", conn, params=p)
    conn.close()
    return jsonify(df.to_dict(orient="records"))

@app.route("/api/telemetry/sarvam", methods=["GET"])
@require_api_key
def get_sarvam_events():
    start = request.args.get("start")
    end = request.args.get("end")
    app_name = request.args.get("app")
    
    conn = get_db()
    q = "SELECT * FROM sarvam_events WHERE date(timestamp) BETWEEN ? AND ?"
    p = [start, end]
    if app_name and app_name != "All":
        q += " AND app_name=?"
        p.append(app_name)
    df = pd.read_sql_query(q + " ORDER BY timestamp DESC", conn, params=p)
    conn.close()
    return jsonify(df.to_dict(orient="records"))

@app.route("/api/telemetry/apps", methods=["GET"])
@require_api_key
def get_apps():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT app_name FROM llm_events UNION SELECT DISTINCT app_name FROM sarvam_events").fetchall()
    conn.close()
    return jsonify([r[0] for r in rows if r[0]])

if __name__ == "__main__":
    print(f"Starting Secure Telemetry API with key: {API_KEY}")
    app.run(host="127.0.0.1", port=5005)
