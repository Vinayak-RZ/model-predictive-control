# Notes for future agents

## Repo purpose

Coursework lab: offset-free SISO MPC vs PID vs scenario-tuned PID on a CasADi induction-heater twin (`src/mpc_core/`, Streamlit `app.py`, showcase `video/`). Educational / illustrative parameters only.

## Branching and report work

- Academic PDF lives under `report/` (`main.tex`, `report.pdf`, `figures/`, `metrics_summary.json`). Rebuild with `bash scripts/rebuild_academic_report.sh` from the repo root (see `report/README.md`).
- Retuned MPC defaults (reference preview, `N=40`, `Qt=50`, power scenario `N=45`) are in source: `mpc.py`, `sim/config.py`, `sim/simulate.py`, `sim/scenarios.py`, `sim/playground.py`. Tests in `tests/` must stay green (`pytest`).
- When metrics or claims change, update `README.md` proof table, `results/` JSON/plots/markdown, and `report/report.md` / `HOW-IT-WORKS.md` **in the same change set** as the number change. Never invent figures for the PDF; run the rebuild scripts.
- Prefer Conventional Commits, lowercase imperative, small focused commits. Commit identity for this repo: `Vinayak-RZ <179278780+Vinayak-RZ@users.noreply.github.com>`. No force-push to shared branches.

## Hard constraints

- Do not use the course-forbidden product or part codenames in prose, code, or docs. Run the pre-PR content grep from the course brief before opening a pull request.
- Say **induction heater** once, then **heater**. British spelling in the academic report.
- Do not commit secrets, `.venv/`, or large unrelated binaries. `report/report.pdf` and `report/figures/` are intentional deliverables.

## Useful entry points

| Task | Start here |
| --- | --- |
| MPC solve / preview / terminal cost | `src/mpc_core/mpc.py` |
| Closed-loop batch + mismatch / ambient | `src/mpc_core/sim/simulate.py`, `scripts/rebuild_report_metrics.py` |
| Defaults and playground knobs | `src/mpc_core/sim/config.py`, `playground.py` |
| Course PDF | `report/main.tex`, `report/README.md` |
| UI | `app.py`, `pages/` |
