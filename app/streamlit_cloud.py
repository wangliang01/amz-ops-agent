from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Streamlit Community Cloud has no separate API process. Run the graph in this
# process and keep the demo on the rule-based fallback unless a key is supplied.
try:
    import streamlit as st

    _secrets = st.secrets
except Exception:
    _secrets = {}

for _key in (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "CHAT_MODEL",
    "CHEAP_MODEL",
    "MODEL_PRICE_INPUT",
    "MODEL_PRICE_OUTPUT",
    "LLM_ENABLED",
    "EMBEDDING_ENABLED",
    "TOP_K",
    "MAX_TOKENS",
):
    try:
        if _key in _secrets and _key not in os.environ:
            os.environ[_key] = str(_secrets[_key])
    except Exception:
        break

os.environ.setdefault("API_BASE_URL", "local")
os.environ.setdefault("EMBEDDING_ENABLED", "false")

# Streamlit Cloud normally allows writes in the app directory, but SQLite must
# never make the app fail to boot if the checkout is mounted read-only.
_data_dir = ROOT / "data"
if not os.access(_data_dir, os.W_OK):
    _runtime = Path(tempfile.gettempdir()) / "amz-ops-agent"
    _runtime.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("RUNS_DB_PATH", str(_runtime / "runs.sqlite"))
    os.environ.setdefault(
        "CHECKPOINT_DB_PATH", str(_runtime / "checkpoints.sqlite")
    )

from app.streamlit_app import main

main()
