"""Load the cited reference values in ``validation/reference_data``."""

from __future__ import annotations

import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent / "reference_data"


def load(name: str) -> list[dict[str, str]]:
    with open(DATA / name) as f:
        rows = [line for line in f if not line.startswith("#")]
    return list(csv.DictReader(rows))


def _row(name: str, engine: str) -> dict[str, str]:
    for row in load(name):
        if row["engine"] == engine:
            return row
    raise KeyError(engine)


def icao(engine: str) -> dict:
    """ICAO Engine Emissions Databank (Issue 32) row, numbers converted to SI floats."""
    r = _row("icao_eedb.csv", engine)
    out = {k: float(r[k]) for k in r if k not in ("engine", "uid", "source")}
    out["rated_thrust"] = out.pop("rated_thrust_kN") * 1e3
    out.update(engine=r["engine"], uid=r["uid"], source=r["source"])
    return out


def tcds(engine: str) -> dict:
    """EASA type-certificate data sheet values (thrust converted to N)."""
    r = _row("tcds.csv", engine)
    return {
        "engine": r["engine"],
        "takeoff_thrust": float(r["takeoff_thrust_daN"]) * 10.0,
        "max_continuous_thrust": float(r["max_continuous_thrust_daN"]) * 10.0,
        "egt_limit_takeoff_C": float(r["egt_limit_takeoff_C"]),
        "egt_station": r["egt_station"],
        "dry_weight_kg": float(r["dry_weight_kg"]),
        "source": r["source"],
    }


# ICAO LTO cycle thrust settings (Annex 16 Vol. II): fraction of rated thrust per mode
LTO_MODES = (("takeoff", 1.00), ("climbout", 0.85), ("approach", 0.30), ("idle", 0.07))
