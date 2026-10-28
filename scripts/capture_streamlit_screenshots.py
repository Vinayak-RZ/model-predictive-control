"""Capture Streamlit UI screenshots for the README."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

DOCS = Path(__file__).resolve().parents[1] / "docs"
URL = "http://127.0.0.1:8501/"


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(DOCS / "streamlit-scenario-controls.png"), full_page=True)

        run_btn = page.get_by_role("button", name="Run simulation")
        run_btn.click()
        page.wait_for_timeout(8000)
        page.screenshot(path=str(DOCS / "streamlit-comparison-plots.png"), full_page=True)

        metrics = page.get_by_text("Metrics", exact=True).first
        if metrics.count():
            metrics.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
        page.screenshot(path=str(DOCS / "streamlit-metrics-table.png"), full_page=True)
        browser.close()
    print("Wrote docs/streamlit-*.png")


if __name__ == "__main__":
    main()
