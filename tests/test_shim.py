import telemetry as _tel
import sys
from pathlib import Path

# Add src to path just in case the shim needs it (though it does import src.core.telemetry)
sys.path.append(str(Path.cwd()))

print("Testing ROOT SHIM log_sarvam_call without trace_id...")
try:
    _tel.log_sarvam_call(
        app_name="audio_insight_engine",
        audio_source="test_source",
        audio_duration_sec=10.0,
        latency_ms=100.0,
        language_code="ta-IN",
        num_chunks=1
    )
    print("Success! Shim correctly forwarded the call with default trace_id.")
except TypeError as e:
    print(f"Shim FAILED with TypeError: {e}")
except Exception as e:
    print(f"Shim FAILED with Error: {e}")
