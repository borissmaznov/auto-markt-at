"""SQLite storage for aggregated registrations."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS registrations (
    year      INTEGER NOT NULL,
    make      TEXT    NOT NULL,
    model     TEXT    NOT NULL,
    fuel      TEXT    NOT NULL,   -- electric, petrol, diesel, petrol/electric, ...
    fuel_mode TEXT    NOT NULL,   -- E electric, P plug-in hybrid, H hybrid, M mono fuel, ...
    regs      INTEGER NOT NULL,
    co2       REAL,               -- average WLTP CO2 g/km
    kw        REAL,               -- average engine power
    kg        REAL,               -- average mass in running order
    whkm      REAL,               -- average electric consumption Wh/km
    PRIMARY KEY (year, make, model, fuel, fuel_mode)
);

-- drive type in one place, so every query uses the same definition
CREATE VIEW IF NOT EXISTS registrations_typed AS
SELECT *,
       CASE
           WHEN fuel = 'electric' THEN 'BEV'
           WHEN fuel_mode = 'P' THEN 'PHEV'
           WHEN fuel_mode = 'H' OR fuel LIKE '%/electric' THEN 'HEV'  -- full hybrids often come as petrol + mode H
           ELSE 'ICE'
       END AS drive
FROM registrations;
"""


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def load(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Insert or replace rows; a re-download of a year simply overwrites it."""
    conn.executemany(
        """
        INSERT INTO registrations (year, make, model, fuel, fuel_mode, regs, co2, kw, kg, whkm)
        VALUES (:year, :make, :model, :fuel, :fuel_mode, :regs, :co2, :kw, :kg, :whkm)
        ON CONFLICT (year, make, model, fuel, fuel_mode) DO UPDATE SET
            regs = excluded.regs, co2 = excluded.co2, kw = excluded.kw, kg = excluded.kg, whkm = excluded.whkm
        """,
        rows,
    )
    conn.commit()
    return len(rows)
