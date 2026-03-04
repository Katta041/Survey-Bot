import sys
from pathlib import Path

# Add project root to path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Run the modular app directly (no __main__ guard — Streamlit needs this to run at module level)
with open(root_dir / "apps" / "survey_chatbot" / "app.py") as f:
    code = compile(f.read(), "apps/survey_chatbot/app.py", 'exec')
    exec(code, globals())
