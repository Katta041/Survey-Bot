import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if it exists
load_dotenv()

class Config:
    # ─── PATHS ─────────────────────────────────────────────────────────────
    BASE_DIR = Path("/Users/aierarohit/Desktop/Political Data").resolve()
    
    # Source directories
    SRC_DIR = BASE_DIR / "src"
    APPS_DIR = BASE_DIR / "apps"
    
    # Data directories
    DATA_DIR = BASE_DIR / "data"
    DB_DIR = DATA_DIR / "db"
    RAW_DATA_DIR = DATA_DIR / "raw"
    RESULTS_DIR = DATA_DIR / "results"
    
    # Asset directories
    ASSETS_DIR = BASE_DIR / "assets"
    LOGOS_DIR = ASSETS_DIR / "logos"
    
    # Media directories
    AUDIO_DIR = DATA_DIR / "audio_samples"
    SARVAM_OUTPUTS_DIR = DATA_DIR / "sarvam_outputs"
    
    # Priority: Environment variable (.env)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
    
    # ─── DATABASE ──────────────────────────────────────────────────────────
    TELEMETRY_DB_PATH = DB_DIR / "telemetry.db"
    
    # ─── MODELS ────────────────────────────────────────────────────────────
    LLM_MODEL = "gpt-4o"
    TRANSCRIPTION_MODEL = "whisper-1"
    SARVAM_MODEL = "saaras:v3"

    @classmethod
    def ensure_dirs(cls):
        """Ensure all required directories exist."""
        directories = [
            cls.DB_DIR, cls.RAW_DATA_DIR, cls.RESULTS_DIR,
            cls.LOGOS_DIR, cls.AUDIO_DIR, cls.SARVAM_OUTPUTS_DIR
        ]
        for d in directories:
            d.mkdir(parents=True, exist_ok=True)

# Auto-ensure directories on import for convenience
Config.ensure_dirs()
