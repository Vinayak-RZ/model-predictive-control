#!/usr/bin/env python3
"""Batch MPC vs PID simulations; writes PNG figures and metrics under results/."""

from __future__ import annotations

import json
from pathlib import Path

from mpc_core.sim.plotting import format_metrics_table, save_comparison_figure
from mpc_core.sim.scenarios import SCENARIOS
from mpc_core.sim.simulate import run_closed_loop


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, dict[str, dict[str, float | int | None]]] = {}

    for key, scenario in SCENARIOS.items():
        mpc = run_closed_loop(scenario, "mpc")
        pid = run_closed_loop(scenario, "pid")
        png = out_dir / f"{key}.png"
        save_comparison_figure(
            title=scenario.title,
            mpc=mpc,
            pid=pid,
            path=png,
        )
        summary[key] = {
            "mpc": mpc.metrics.__dict__,
            "pid": pid.metrics.__dict__,
        }
        md_path = out_dir / f"{key}_metrics.md"
        md_path.write_text(
            f"# {scenario.title}\n\n{scenario.description}\n\n"
            f"{format_metrics_table(mpc.metrics, pid.metrics)}\n",
            encoding="utf-8",
        )
        print(f"Wrote {png}")

    (out_dir / "metrics_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(f"Done. Figures in {out_dir}")


if __name__ == "__main__":
    main()
