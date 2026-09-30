"""Export a star schema as CSV for Power BI: one fact table and three small dimensions.

Power BI loads the files straight from GitHub (see powerbi/load.pq), so the dashboard refreshes whenever the
exported data in the repository is updated.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from . import FOCUS_MAKES
from .eea import PROVISIONAL

# Column names repeat only for the join keys: Power BI auto-detects relationships by column name, and two
# plain "label" columns would link dim_year to dim_drive.
DRIVES = [  # drive, German label, sort order in visuals
    ("BEV", "E-Auto", 1),
    ("PHEV", "Plug-in-Hybrid", 2),
    ("HEV", "Vollhybrid", 3),
    ("ICE", "Verbrenner", 4),
]


def _write(path: Path, header: list[str], rows) -> int:
    count = 0
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in rows:
            w.writerow(row)
            count += 1
    return count


def _num(value, digits: int = 1):
    return "" if value is None else round(float(value), digits)


def export_star(conn: sqlite3.Connection, out_dir: str | Path = "powerbi/data",
                focus: tuple[str, ...] = FOCUS_MAKES) -> dict[str, int]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    facts = conn.execute(
        "SELECT year, make, model, drive, fuel, regs, co2, kw, kg, whkm FROM registrations_typed "
        "ORDER BY year, make, model"
    )
    counts = {
        "fact_registrations": _write(
            out / "fact_registrations.csv",
            ["year", "make", "model", "drive", "fuel", "regs", "co2_g_km", "power_kw", "mass_kg", "consumption_wh_km"],
            ([r["year"], r["make"], r["model"], r["drive"], r["fuel"], r["regs"], _num(r["co2"]), _num(r["kw"]),
              _num(r["kg"], 0), _num(r["whkm"])] for r in facts),
        )
    }
    makes = [r[0] for r in conn.execute("SELECT DISTINCT make FROM registrations ORDER BY make")]
    counts["dim_make"] = _write(
        out / "dim_make.csv", ["make", "brand", "focus_brand"],
        ([m, m if len(m) <= 3 else m.title(), "ja" if m in focus else "nein"] for m in makes),
    )
    years = [r[0] for r in conn.execute("SELECT DISTINCT year FROM registrations ORDER BY year")]
    counts["dim_year"] = _write(
        out / "dim_year.csv", ["year", "year_label", "provisional"],
        ([y, f"{y}*" if y in PROVISIONAL else str(y), int(y in PROVISIONAL)] for y in years),
    )
    counts["dim_drive"] = _write(out / "dim_drive.csv", ["drive", "drive_label", "drive_sort"], DRIVES)
    return counts
