"""Put ``src/`` on ``sys.path`` so ``import mpc_core`` works without ``pip install -e .``.

Streamlit Community Cloud installs only ``requirements.txt`` (PyPI packages). Editable
local installs are unreliable there; this is the supported workaround for a src layout.
Imported first from ``app.py`` and each ``ui_pages`` script.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
