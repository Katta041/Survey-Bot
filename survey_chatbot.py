import streamlit as st
import sys
from pathlib import Path

# Add project root to path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Redirect to the new modular app
if __name__ == "__main__":
    with open(root_dir / "apps" / "survey_chatbot" / "app.py") as f:
        code = compile(f.read(), "apps/survey_chatbot/app.py", 'exec')
        exec(code, globals())
