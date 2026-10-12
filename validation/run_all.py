"""Regenerate every validation figure and results table.

Run with ``uv run python validation/run_all.py``.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = [
    "cycle_validation.py",
    "engine_validation.py",
    "trade_studies.py",
]

if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    for name in SCRIPTS:
        print(f"== {name}")
        runpy.run_path(str(HERE / name), run_name="__main__")
