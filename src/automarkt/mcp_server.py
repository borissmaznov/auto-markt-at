"""MCP server: an LLM client can ask market questions and gets answers straight from SQL.

Register in Claude Code:  claude mcp add auto-markt -- automarkt --db data/automarkt.db mcp
"""

from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer

from . import FOCUS_MAKES, analytics
from .db import connect

mcp = MCPServer(
    "auto-markt-at", instructions="Official EEA new car registrations in Austria. Drive types: BEV, PHEV, HEV, ICE."
)
_conn = None


def conn():
    global _conn
    if _conn is None:
        _conn = connect(os.getenv("AUTOMARKT_DB", "data/automarkt.db"))
    return _conn


@mcp.tool()
def market_overview() -> list[dict]:
    """New car registrations in Austria per year with the share of electric cars (BEV) and plug-in hybrids."""
    return analytics.market_overview(conn())


@mcp.tool()
def brand_trend(makes: list[str] | None = None) -> list[dict]:
    """Registrations per make and year, growth vs. previous year and BEV share.
    Default makes: Hyundai, MG, BYD, Mitsubishi."""
    return analytics.brand_trend(conn(), tuple(m.upper() for m in (makes or FOCUS_MAKES)))


@mcp.tool()
def brand_ranking(year: int, drive: str = "BEV", limit: int = 10) -> list[dict]:
    """Makes ranked by registrations for one drive type (BEV, PHEV, HEV or ICE) in a year, with market share."""
    return analytics.brand_ranking(conn(), year, drive.upper(), limit)


@mcp.tool()
def top_models(year: int, drive: str = "BEV", make: str | None = None, limit: int = 10) -> list[dict]:
    """Best-selling models for a year and drive type, optionally for one make, with average consumption."""
    return analytics.top_models(conn(), year, drive.upper(), make, limit)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
