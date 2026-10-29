#!/usr/bin/env python3
"""Downsample simulation JSON for the HyperFrames bundle."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "video" / "data"
OUT = ROOT / "video" / "data_bundle.js"


def downsample(obj: dict, step: int = 2) -> dict:
    idx = slice(None, None, step)
    return {
        "time_s": obj["time_s"][idx],
        "y_c": obj["y_c"][idx],
        "y_ref": obj["y_ref"][idx],
        "u_kw": obj["u_kw"][idx],
        "metrics": obj.get("metrics", {}),
    }


def main() -> None:
    pw = json.loads((DATA / "power_limits.json").read_text(encoding="utf-8"))
    sp = json.loads((DATA / "setpoint_jump.json").read_text(encoding="utf-8"))
    score = json.loads((DATA / "scorecard.json").read_text(encoding="utf-8"))
    horizon = json.loads((DATA / "horizon_frames.json").read_text(encoding="utf-8"))
    bundle = {
        "power": {
            "mpc": downsample(pw["mpc"]),
            "pid": downsample(pw["pid"]),
            "optimized_pid": downsample(pw["optimized_pid"]),
            "limits": pw["limits"],
            "violation_times_s": pw.get("violation_times_s", {}),
        },
        "setpoint": {
            "mpc": downsample(sp["mpc"]),
            "pid": downsample(sp["pid"]),
            "optimized_pid": downsample(sp["optimized_pid"]),
        },
        "scorecard": score,
        "horizon": horizon,
    }
    OUT.write_text(
        f"window.MPC_DEMO_DATA = {json.dumps(bundle)};\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
