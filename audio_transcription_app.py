import streamlit as st
import sys
from pathlib import Path

# Add project root and src to path for modular imports
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Import the refactored app logic
try:
    from apps.audio_transcription.app import main
    if __name__ == "__main__":
        main()
except ImportError:
    # If the app isn't structured as a function yet, we can just run the file content
    # But for now, I'll just make this file a direct copy or a clean redirect
    pass

# Simplified redirect: Running the actual app content
if __name__ == "__main__":
    with open(root_dir / "apps" / "audio_transcription" / "app.py") as f:
        code = compile(f.read(), "apps/audio_transcription/app.py", 'exec')
        exec(code, globals())
