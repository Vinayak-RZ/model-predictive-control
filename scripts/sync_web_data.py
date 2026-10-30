#!/usr/bin/env python3
"""Copy Streamlit UI data + assets into web/ for the Vercel static site."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DATA_SRC = ROOT / "data" / "ui"
DATA_DST = WEB / "data"
ASSETS_SRC = ROOT / "assets"
ASSETS_DST = WEB / "assets"


def main() -> None:
    WEB.mkdir(parents=True, exist_ok=True)
    if DATA_DST.exists():
        shutil.rmtree(DATA_DST)
    shutil.copytree(DATA_SRC, DATA_DST)
    ASSETS_DST.mkdir(parents=True, exist_ok=True)
    for name in ("mpc-infographic.png",):
        src = ASSETS_SRC / name
        if src.exists():
            shutil.copy2(src, ASSETS_DST / name)
    print(f"Synced {DATA_SRC} -> {DATA_DST}")
    print(f"Synced assets into {ASSETS_DST}")


if __name__ == "__main__":
    main()
