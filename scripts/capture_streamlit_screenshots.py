"""Capture Streamlit multipage UI screenshots for README and video."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
VIDEO_ASSETS = ROOT / "video" / "assets"
BASE = "http://127.0.0.1:8501"


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    VIDEO_ASSETS.mkdir(parents=True, exist_ok=True)
    shots = [
        ("Playground", DOCS / "streamlit-playground.png", VIDEO_ASSETS / "ui-playground.png"),
        ("Step_through", DOCS / "streamlit-step-through.png", None),
        ("Scorecard", DOCS / "streamlit-scorecard.png", VIDEO_ASSETS / "ui-scorecard.png"),
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        for page_name, doc_path, video_path in shots:
            page.goto(f"{BASE}/{page_name}", wait_until="networkidle")
            page.wait_for_timeout(6000 if page_name == "Playground" else 3500)
            page.screenshot(path=str(doc_path), full_page=True)
            if video_path:
                page.screenshot(path=str(video_path), full_page=True)
            print(f"Wrote {doc_path}")
        browser.close()


if __name__ == "__main__":
    main()
