"""
Generate the synthetic demo data that ships with this repository.

Everything produced here is fictional: respondent IDs, answers, transcripts,
audio and telemetry are generated from a fixed random seed. No real survey
record, recording or person is used.

Outputs (paths relative to the repo root):
  data/production/tn_survey_sanitized.csv   survey dataset used by the chatbot
  data/audio_samples/*.wav                  tiny generated audio files
  data/db/telemetry.db                      telemetry events for the dashboard

Usage:
  python scripts/generate_synthetic_data.py            # everything
  python scripts/generate_synthetic_data.py --telemetry-only
"""
import argparse
import csv
import datetime
import math
import random
import sqlite3
import struct
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROD_CSV = ROOT / "data" / "production" / "tn_survey_sanitized.csv"
AUDIO_DIR = ROOT / "data" / "audio_samples"
DB_PATH = ROOT / "data" / "db" / "telemetry.db"

SEED = 20260301
N_ROWS = 240

COLUMNS = [
    "sample_id", "url", "transcript", "qc_status", "qc_score", "qc_comment",
    "MLA_Satisfaction", "Desires_Change", "Next_CM", "Vote_2026",
    "Caste", "Age_Group", "Gender", "Occupation",
]

# Answer options use the same bilingual labels as the questionnaire the code was
# written for. The weights are arbitrary and do not reflect any real opinion.
MLA = [("திருப்தி/ Satisfied", 3), ("திருப்தியில்லை/ Not Satisfied", 3), ("மேம்பாடு தேவை/ Needs improvement", 2)]
CHANGE = [("ஆம், மாற்றம் தேவை/ Yes, need a change", 4), ("இல்லை, மாற்றம் தேவையில்லை/ No, don’t need a change", 4), ("உறுதி இல்லை/ Not sure", 1)]
NEXT_CM = [
    ("விஜய் (தமிழகம் வெற்றி கழகம்)/ Vijay (TVK)", 3),
    ("மு.க. ஸ்டாலின் (திமுக)/ M.K. Stalin (DMK)", 3),
    ("எடப்பாடி கே. பழனிசாமி (அதிமுக)/ Edappadi K. Palaniswami (AIADMK)", 2),
    ("சீமான் (நாம் தமிழர் கட்சி)/ Seeman (NTK)", 1),
    ("மற்றவர்கள்/ Others", 1),
]
CM_TO_PARTY = {
    NEXT_CM[0][0]: "தமிழகம் வெற்றி கழகம்/ Tamilaga Vettri Kazhagam(TVK)",
    NEXT_CM[1][0]: "திமுக கூட்டணி/ DMK Alliance",
    NEXT_CM[2][0]: "அதிமுக கூட்டணி/ AIADMK Alliance",
    NEXT_CM[3][0]: "நாம் தமிழர் கட்சி/ Naam Tamilar Katch(NTK)",
    NEXT_CM[4][0]: "மற்றவர்கள்/ Others",
}
CASTE = [("Fisherman", 4), ("SC", 3), ("Vanniyar", 3), ("Linguistic Minority", 2), ("Nadars", 2),
         ("Chettiyar", 1), ("Mudaliyar", 1), ("Muslim", 1), ("Christian", 1), ("ST", 1), ("DONT SAY", 1)]
AGE = [("18-30", 3), ("31-40", 3), ("41-60", 3), ("60+", 1)]
GENDER = [("பெண்/Female", 1), ("ஆண்/Male", 1)]
OCCUPATION = [("இல்லத்தரசி/ Housewife", 3), ("கூலி தொழில்/ Daily Wage", 3),
              ("சொந்த தொழில் / சுயதொழில் செய்பவர்/ Self Employed/Business", 2),
              ("பணியாளர்/ Employee", 1), ("மாணவர்/ Student", 1), ("மற்றவை/ Others", 1)]

# Transcript building blocks, written for this demo (not taken from any recording).
INTRO = [
    "வணக்கம், நாங்க ஒரு கருத்துக்கணிப்பு செய்கிறோம், சில கேள்விகள் கேட்கலாமா?",
    "வணக்கம் அம்மா, இரண்டு நிமிஷம் பேசலாமா? இது ஒரு சர்வே.",
    "Hello sir, oru small survey, few questions mattum.",
]
MLA_LINES = {
    MLA[0][0]: ["எம்.எல்.ஏ வேலை பரவாயில்லை, அடிக்கடி ஏரியாவுக்கு வருவார்.", "MLA work okay, he came during the rain time."],
    MLA[1][0]: ["எம்.எல்.ஏ இங்க வந்ததே இல்லை, எந்த வேலையும் நடக்கல.", "MLA-va paathathe illa, no work happened here."],
    MLA[2][0]: ["கொஞ்சம் வேலை நடந்திருக்கு, ஆனா இன்னும் நிறைய செய்யணும்.", "Some work done, but still lot of improvement needed."],
}
ISSUES = [
    ("roads", ["எங்க தெரு சாலை ரொம்ப மோசம், மழை வந்தா நடக்கவே முடியாது.", "ரோடு போட்டு இரண்டு வருஷம் ஆச்சு, மறுபடியும் பள்ளம் ஆயிடுச்சு.", "The road near the bus stop is a big problem, please fix it."]),
    ("water", ["குடிநீர் வாரத்துக்கு இரண்டு நாள் தான் வருது, அது பெரிய பிரச்சனை.", "Water supply is irregular, we buy cans every day."]),
    ("drainage", ["கழிவுநீர் கால்வாய் அடைச்சு கிடக்கு, கொசு தொல்லை அதிகம்.", "Drainage overflow every monsoon, health issue for kids."]),
    ("prices", ["விலைவாசி ரொம்ப ஏறிப்போச்சு, காய்கறி வாங்கவே கஷ்டம்.", "Gas cylinder price is too high for daily wage families."]),
    ("jobs", ["இளைஞர்களுக்கு வேலை வாய்ப்பு இல்லை, அதுதான் முக்கிய கோரிக்கை.", "Youth need jobs, factories should come to this area."]),
    ("schemes", ["மகளிர் உரிமைத் தொகை கிடைக்குது, அது உதவியா இருக்கு.", "இலவச பஸ் பயணம் பெண்களுக்கு நல்ல திட்டம்.", "Ration shop is fine but queue is very long."]),
    ("health", ["அரசு மருத்துவமனையில் டாக்டர் குறைவு, காத்திருக்கணும்.", "Primary health centre needs more staff and medicines."]),
    ("fishing", ["மீன்பிடி துறைமுகம் சரியா பராமரிக்கப்படல, படகு நிறுத்த இடம் இல்லை.", "Fishermen need better harbour facilities and relief during ban period."]),
]
CHANGE_LINES = {
    CHANGE[0][0]: ["ஆமாம், இந்த தடவை மாற்றம் வேணும்.", "Yes, change venum this time."],
    CHANGE[1][0]: ["இப்போ இருக்குற ஆட்சியே போதும், மாற்றம் தேவையில்லை.", "No change needed, current government is okay."],
    CHANGE[2][0]: ["இன்னும் முடிவு பண்ணல, பார்க்கலாம்.", "Not decided yet, will see closer to election."],
}
CM_LINES = {
    NEXT_CM[0][0]: ["அடுத்த முதல்வரா விஜய் வரணும்னு நினைக்கிறேன், புதுசா ஒருத்தர் வேணும்.", "I like Vijay, new face, youngsters support him."],
    NEXT_CM[1][0]: ["ஸ்டாலின் தான் தொடரணும், திட்டங்கள் நல்லா இருக்கு.", "Stalin is doing okay, schemes are useful for us."],
    NEXT_CM[2][0]: ["எடப்பாடி ஆட்சி காலத்துல நல்லா இருந்துச்சு.", "AIADMK time was better for our area."],
    NEXT_CM[3][0]: ["சீமான் பேசுறது சரியா இருக்கு, தமிழ் உணர்வு முக்கியம்.", "Seeman speaks for Tamil people, I support NTK."],
    NEXT_CM[4][0]: ["யாரு வந்தாலும் ஒண்ணுதான், வேலை செய்யணும் அவ்வளவுதான்.", "Anyone is fine, they should just do the work."],
}
CLOSING = ["நன்றி.", "சரி, நன்றி அம்மா.", "Thank you sir.", "நன்றி, வணக்கம்."]
EMPTY_AUDIO = ["", "ஹலோ... ஹலோ...", "(background noise)"]


def pick(rng, options):
    values, weights = zip(*options)
    return rng.choices(values, weights=weights, k=1)[0]


def build_transcript(rng, row):
    parts = [rng.choice(INTRO), rng.choice(MLA_LINES[row["MLA_Satisfaction"]])]
    for _, lines in rng.sample(ISSUES, k=rng.randint(1, 3)):
        parts.append(rng.choice(lines))
    parts.append(rng.choice(CHANGE_LINES[row["Desires_Change"]]))
    parts.append(rng.choice(CM_LINES[row["Next_CM"]]))
    parts.append(rng.choice(CLOSING))
    return " ".join(parts)


def generate_survey(rng):
    rows = []
    for i in range(1, N_ROWS + 1):
        sid = f"SYN-{i:04d}"
        row = {
            "sample_id": sid,
            "url": f"https://example.com/synthetic-audio/{sid}.mp3",
            "MLA_Satisfaction": pick(rng, MLA),
            "Desires_Change": pick(rng, CHANGE),
            "Next_CM": pick(rng, NEXT_CM),
            "Caste": pick(rng, CASTE),
            "Age_Group": pick(rng, AGE),
            "Gender": pick(rng, GENDER),
            "Occupation": pick(rng, OCCUPATION),
        }
        # Most respondents vote for the party of their preferred CM.
        row["Vote_2026"] = CM_TO_PARTY[row["Next_CM"]] if rng.random() < 0.85 else CM_TO_PARTY[pick(rng, NEXT_CM)]
        if rng.random() < 0.5:
            row.update(qc_status="Pending", qc_score="", qc_comment="No comment")
        elif rng.random() < 0.1:
            row.update(qc_status="Done", qc_score="10.0", qc_comment="Fake Audio/Empty Audio")
        else:
            score = rng.choice([80.0, 90.0, 90.0, 95.0, 100.0])
            row.update(qc_status="Done", qc_score=str(score), qc_comment="Correctly Done")
        row["transcript"] = rng.choice(EMPTY_AUDIO) if row["qc_comment"] == "Fake Audio/Empty Audio" else build_transcript(rng, row)
        rows.append(row)
    PROD_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(PROD_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {PROD_CSV.relative_to(ROOT)} ({len(rows)} rows)")


def write_wav(path, seconds, freq=None, rate=16000):
    """Write a mono 16-bit WAV: a sine tone at `freq` Hz, or silence when freq is None."""
    frames = bytearray()
    for n in range(int(seconds * rate)):
        value = 0 if freq is None else int(0.3 * 32767 * math.sin(2 * math.pi * freq * n / rate))
        frames += struct.pack("<h", value)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


def generate_audio():
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    write_wav(AUDIO_DIR / "synthetic_tone_440hz.wav", 1.0, freq=440)
    write_wav(AUDIO_DIR / "synthetic_tone_880hz.wav", 0.5, freq=880)
    write_wav(AUDIO_DIR / "synthetic_silence.wav", 1.0, freq=None)
    print(f"wrote 3 WAV files to {AUDIO_DIR.relative_to(ROOT)}")


def generate_telemetry(rng, days=30):
    """Seed the dashboard with fictional events dated over the last `days` days."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE llm_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, app_name TEXT, model TEXT, query_type TEXT,
        user_query TEXT, response_preview TEXT, input_tokens INTEGER, output_tokens INTEGER,
        cost_usd REAL, latency_ms REAL, timestamp TEXT)""")
    conn.execute("""CREATE TABLE sarvam_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, app_name TEXT, audio_source TEXT,
        audio_duration_sec REAL, cost_usd REAL, latency_ms REAL,
        language_code TEXT, num_chunks INTEGER, timestamp TEXT)""")
    questions = [
        ("decision", "Who do people support for next CM?"),
        ("decision", "Break down CM support by caste"),
        ("qualitative_synthesis", "What do people say about roads?"),
        ("qualitative_synthesis", "What are people's main concerns?"),
        ("decision", "Do people want a change in government?"),
    ]
    now = datetime.datetime.utcnow()
    for _ in range(160):
        ts = now - datetime.timedelta(days=rng.uniform(0, days), minutes=rng.uniform(0, 600))
        app = rng.choice(["survey_chatbot_tn", "audio_insight_engine"])
        qtype, q = rng.choice(questions)
        tin, tout = rng.randint(400, 3200), rng.randint(40, 600)
        cost = (tin * 2.50 + tout * 10.00) / 1_000_000
        conn.execute(
            "INSERT INTO llm_events (app_name, model, query_type, user_query, response_preview, input_tokens, output_tokens, cost_usd, latency_ms, timestamp) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (app, "gpt-4o", qtype, q, "Synthetic response preview.", tin, tout, round(cost, 8), round(rng.uniform(600, 4500), 1), ts.isoformat()),
        )
    for _ in range(40):
        ts = now - datetime.timedelta(days=rng.uniform(0, days), minutes=rng.uniform(0, 600))
        dur = rng.uniform(20, 240)
        conn.execute(
            "INSERT INTO sarvam_events (app_name, audio_source, audio_duration_sec, cost_usd, latency_ms, language_code, num_chunks, timestamp) VALUES (?,?,?,?,?,?,?,?)",
            ("audio_insight_engine", rng.choice(["uploaded_file", "url"]), round(dur, 2), round(dur / 60 * 0.005, 8),
             round(rng.uniform(1500, 12000), 1), "ta-IN", math.ceil(dur / 28), ts.isoformat()),
        )
    conn.commit()
    conn.close()
    print(f"wrote {DB_PATH.relative_to(ROOT)} (200 events over the last {days} days)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--telemetry-only", action="store_true", help="only re-seed data/db/telemetry.db with fresh dates")
    args = parser.parse_args()
    rng = random.Random(SEED)
    if not args.telemetry_only:
        generate_survey(rng)
        generate_audio()
    generate_telemetry(random.Random(SEED + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
