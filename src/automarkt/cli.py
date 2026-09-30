"""Command line: `automarkt fetch | report | ask-sql | mcp`."""

from __future__ import annotations

import argparse
import json
import logging
import os

from . import analytics
from .db import connect, load
from .eea import SOURCES, fetch_all


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="automarkt", description="Austrian new car market from EEA open data")
    parser.add_argument("--db", default=os.getenv("AUTOMARKT_DB", "data/automarkt.db"), help="SQLite file")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_fetch = sub.add_parser("fetch", help="download aggregated registrations from the EEA API")
    p_fetch.add_argument("--years", type=int, nargs="*", default=list(SOURCES))
    p_report = sub.add_parser("report", help="write report/marktbericht.md and the SVG chart")
    p_report.add_argument("--out", default="report")
    p_show = sub.add_parser("show", help="print one analysis as JSON")
    p_show.add_argument("what", choices=["overview", "brands", "ranking", "models"])
    p_show.add_argument("--year", type=int)
    sub.add_parser("mcp", help="start the MCP server (stdio)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    os.environ["AUTOMARKT_DB"] = args.db

    if args.cmd == "mcp":
        from .mcp_server import main as mcp_main

        mcp_main()
        return

    conn = connect(args.db)
    if args.cmd == "fetch":
        print(json.dumps({"rows": load(conn, fetch_all(args.years))}))
    elif args.cmd == "report":
        from .report import build

        print(build(conn, args.out))
    elif args.cmd == "show":
        year = args.year or max(analytics.years(conn))
        data = {
            "overview": lambda: analytics.market_overview(conn),
            "brands": lambda: analytics.brand_trend(conn),
            "ranking": lambda: analytics.brand_ranking(conn, year),
            "models": lambda: analytics.top_models(conn, year),
        }[args.what]()
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
