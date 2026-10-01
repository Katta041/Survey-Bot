"""Offline checks for the bundled synthetic dataset and the chatbot engine helpers.

Run with `python -m pytest tests/test_synthetic_data.py` or `python -m tests.test_synthetic_data`.
No API calls are made.
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OPENAI_API_KEY", "placeholder-key-for-offline-tests")

import pandas as pd  # noqa: E402

from src.core.config import Config  # noqa: E402
from src.logic.chatbot.engine import SurveyChatEngine  # noqa: E402

CSV = Config.PRODUCTION_DATA_DIR / "tn_survey_sanitized.csv"
EXPECTED = ["sample_id", "url", "transcript", "qc_status", "qc_score", "qc_comment",
            "MLA_Satisfaction", "Desires_Change", "Next_CM", "Vote_2026",
            "Caste", "Age_Group", "Gender", "Occupation"]


def load():
    return pd.read_csv(CSV)


def test_columns_and_ids():
    df = load()
    assert list(df.columns) == EXPECTED
    assert df["sample_id"].str.fullmatch(r"SYN-\d{4}").all()
    assert df["url"].str.startswith("https://example.com/").all()


def test_no_phone_numbers_or_emails():
    text = load().astype(str).to_csv(index=False)
    assert not re.search(r"(?<!\d)(\+91[- ]?)?[6-9]\d{9}(?!\d)", text)
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)


def test_engine_code_and_search():
    df = load()
    df["transcript"] = df["transcript"].astype(str)
    engine = SurveyChatEngine(df)
    counts = engine.execute_code("df['Next_CM'].value_counts()")
    assert int(counts.sum()) == len(df)
    context, citations, total = engine.search_transcripts(["சாலை", "ரோடு", "road"], "roads")
    assert total > 0 and citations and context


def test_audio_samples_exist():
    wavs = sorted(Config.AUDIO_DIR.glob("synthetic_*.wav"))
    assert len(wavs) == 3


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
