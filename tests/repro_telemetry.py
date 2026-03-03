import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path.cwd()))

from src.core.telemetry import log_sarvam_call

print("Testing log_sarvam_call without trace_id...")
try:
    log_sarvam_call(
        app_name="test_app",
        audio_source="test_source",
        audio_duration_sec=10.0,
        latency_ms=100.0,
        language_code="en-US",
        num_chunks=1
    )
    print("Success! No missing argument error.")
except TypeError as e:
    print(f"Caught expected/unexpected TypeError: {e}")
except Exception as e:
    print(f"Other error: {e}")
