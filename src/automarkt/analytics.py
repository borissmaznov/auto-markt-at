"""Market questions answered in SQL (window functions for growth and ranking)."""

from __future__ import annotations

import sqlite3

from . import FOCUS_MAKES


def _rows(cur) -> list[dict]:
    return [dict(r) for r in cur]


def market_overview(conn: sqlite3.Connection) -> list[dict]:
    """Registrations per year and the share of each drive type."""
    return _rows(conn.execute(
        """
        SELECT year,
               SUM(regs)                                                               AS total,
               SUM(CASE WHEN drive = 'BEV' THEN regs ELSE 0 END)                       AS bev,
               ROUND(100.0 * SUM(CASE WHEN drive = 'BEV'  THEN regs ELSE 0 END) / SUM(regs), 1) AS bev_share,
               ROUND(100.0 * SUM(CASE WHEN drive = 'PHEV' THEN regs ELSE 0 END) / SUM(regs), 1) AS phev_share,
               ROUND(100.0 * SUM(CASE WHEN drive = 'HEV'  THEN regs ELSE 0 END) / SUM(regs), 1) AS hev_share
        FROM registrations_typed
        GROUP BY year
        ORDER BY year
        """
    ))


def brand_trend(conn: sqlite3.Connection, makes: tuple[str, ...] = FOCUS_MAKES) -> list[dict]:
    """Registrations per make and year, growth vs. previous year (LAG) and BEV share."""
    marks = ",".join("?" * len(makes))
    return _rows(conn.execute(
        f"""
        WITH per_year AS (
            SELECT make, year, SUM(regs) AS regs,
                   SUM(CASE WHEN drive = 'BEV' THEN regs ELSE 0 END) AS bev
            FROM registrations_typed
            WHERE make IN ({marks})
            GROUP BY make, year
        )
        SELECT make, year, regs, bev,
               ROUND(100.0 * bev / regs, 1) AS bev_share,
               ROUND(100.0 * (regs - LAG(regs) OVER w) / LAG(regs) OVER w, 1) AS growth
        FROM per_year
        WINDOW w AS (PARTITION BY make ORDER BY year)
        ORDER BY make, year
        """,
        [m.upper() for m in makes],
    ))


def brand_ranking(conn: sqlite3.Connection, year: int, drive: str = "BEV", limit: int = 10) -> list[dict]:
    """Makes ranked by registrations of one drive type, with market share."""
    return _rows(conn.execute(
        """
        SELECT RANK() OVER (ORDER BY SUM(regs) DESC)                          AS rank,
               make,
               SUM(regs)                                                     AS regs,
               ROUND(100.0 * SUM(regs) / SUM(SUM(regs)) OVER (), 1)          AS share
        FROM registrations_typed
        WHERE year = ? AND drive = ?
        GROUP BY make
        ORDER BY regs DESC
        LIMIT ?
        """,
        (year, drive, limit),
    ))


def top_models(conn: sqlite3.Connection, year: int, drive: str = "BEV", make: str | None = None,
               limit: int = 10) -> list[dict]:
    sql = """
        SELECT make, model, drive, SUM(regs) AS regs,
               ROUND(SUM(whkm * regs) / NULLIF(SUM(CASE WHEN whkm IS NOT NULL THEN regs END), 0)) AS wh_per_km
        FROM registrations_typed
        WHERE year = ? AND drive = ?
    """
    params: list = [year, drive]
    if make:
        sql += " AND make = ?"
        params.append(make.upper())
    sql += " GROUP BY make, model, drive ORDER BY regs DESC LIMIT ?"
    params.append(limit)
    return _rows(conn.execute(sql, params))


def years(conn: sqlite3.Connection) -> list[int]:
    return [r[0] for r in conn.execute("SELECT DISTINCT year FROM registrations ORDER BY year")]
