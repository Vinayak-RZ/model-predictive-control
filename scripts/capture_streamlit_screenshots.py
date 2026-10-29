"""Capture Streamlit multipage UI screenshots for README.

Requires a running app: streamlit run app.py
Regen: python scripts/capture_streamlit_screenshots.py
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BASE = "http://127.0.0.1:8501"


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    shots = [
        ("", DOCS / "streamlit-overview.png"),
        ("playground", DOCS / "streamlit-playground.png"),
        ("step_through", DOCS / "streamlit-step-through.png"),
        ("scorecard", DOCS / "streamlit-scorecard.png"),
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 960})
        for path, doc_path in shots:
            url = f"{BASE}/{path}" if path else BASE
            page.goto(url, wait_until="networkidle", timeout=120_000)
            page.wait_for_timeout(2500)
            page.screenshot(path=str(doc_path), full_page=True)
            print(f"Wrote {doc_path}")
        browser.close()


if __name__ == "__main__":
    main()
