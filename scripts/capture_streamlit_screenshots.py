"""Capture Streamlit multipage UI screenshots for README.

Requires a running app: streamlit run app.py
Regen: python scripts/capture_streamlit_screenshots.py
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BASE = "http://127.0.0.1:8501"

PAGE_SHOTS = [
    ("", DOCS / "streamlit-overview.png", "MPC Heater Lab"),
    ("playground", DOCS / "streamlit-playground.png", "Playground"),
    ("step_through", DOCS / "streamlit-step-through.png", "Step-through"),
    ("scorecard", DOCS / "streamlit-scorecard.png", "Scorecard"),
]

# Click each preset button; wait for the Active caption to show the case.
PLAYGROUND_PRESET_SHOTS = [
    ("Setpoint jump", DOCS / "streamlit-playground-setpoint.png", "80→120 °C"),
    ("Cold-door", DOCS / "streamlit-playground-cold-door.png", "ambient_step"),
    ("Heat-loss + noise", DOCS / "streamlit-playground-heat-loss-noise.png", "heat_loss_bump"),
    ("Tight power", DOCS / "streamlit-playground-tight-power.png", "u_max=140"),
    ("Soft limits", DOCS / "streamlit-playground-soft-limits.png", "u_max=220"),
    ("Model mismatch", DOCS / "streamlit-playground-mismatch.png", "mismatch on"),
]


def _wait_text(page: Page, text: str, timeout: float = 90_000) -> None:
    page.get_by_text(text, exact=False).first.wait_for(timeout=timeout)


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Page-level shots: fresh context each time.
        for path, out, wait_text in PAGE_SHOTS:
            context = browser.new_context(viewport={"width": 1440, "height": 1200})
            page = context.new_page()
            url = f"{BASE}/{path}" if path else BASE
            page.goto(url, wait_until="domcontentloaded", timeout=120_000)
            _wait_text(page, wait_text)
            page.wait_for_timeout(3500)
            page.screenshot(path=str(out), full_page=True)
            print(f"Wrote {out.name}")
            context.close()

        # Preset shots: one playground session, click through presets.
        context = browser.new_context(viewport={"width": 1440, "height": 1200})
        page = context.new_page()
        page.goto(f"{BASE}/playground", wait_until="domcontentloaded", timeout=120_000)
        _wait_text(page, "Playground")
        page.wait_for_timeout(2500)

        for label, out, marker in PLAYGROUND_PRESET_SHOTS:
            page.get_by_role("button", name=label, exact=True).first.click()
            _wait_text(page, marker)
            page.wait_for_timeout(3500)
            page.screenshot(path=str(out), full_page=True)
            print(f"Wrote {out.name} ({label})")

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
