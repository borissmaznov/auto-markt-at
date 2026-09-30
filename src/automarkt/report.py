"""Market report as Markdown plus an SVG chart, generated from the database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from . import FOCUS_MAKES
from .analytics import brand_ranking, brand_trend, market_overview, top_models, years
from .eea import PROVISIONAL

ACCENT, OTHER = "#0e7c86", "#9aa5b1"


def _fmt(n) -> str:
    return "–" if n is None else f"{n:,.0f}".replace(",", ".")


def _pct(n) -> str:
    return "–" if n is None else f"{n:.1f}".replace(".", ",") + " %"


def _brand(make: str) -> str:
    """Display name: short brands stay upper case (BYD, MG), longer ones in title case (Hyundai)."""
    return make if len(make) <= 3 else make.title()


def _year(y: int) -> str:
    return f"{y}*" if y in PROVISIONAL else str(y)


def ranking_svg(rows: list[dict], focus: tuple[str, ...], title: str) -> str:
    """Horizontal bars, focus makes highlighted. Works on light and dark GitHub themes."""
    bar_h, gap, left, width = 22, 8, 150, 460
    top = 40
    height = top + len(rows) * (bar_h + gap) + 10
    peak = max(r["regs"] for r in rows) or 1
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {left + width + 90} {height}" '
        f'width="{left + width + 90}" height="{height}" font-family="Segoe UI, Helvetica, Arial, sans-serif">',
        "<style>text{fill:#24292f}.muted{fill:#57606a}"
        "@media (prefers-color-scheme: dark){text{fill:#e6edf3}.muted{fill:#9da7b3}}</style>",
        f'<text x="0" y="20" font-size="15" font-weight="600">{title}</text>',
    ]
    for i, r in enumerate(rows):
        y = top + i * (bar_h + gap)
        w = max(2, round(width * r["regs"] / peak))
        color = ACCENT if r["make"] in focus else OTHER
        parts += [
            f'<text x="{left - 10}" y="{y + 16}" font-size="13" text-anchor="end">{_brand(r["make"])}</text>',
            f'<rect x="{left}" y="{y}" width="{w}" height="{bar_h}" rx="3" fill="{color}"/>',
            f'<text x="{left + w + 8}" y="{y + 16}" font-size="12" class="muted">'
            f'{_fmt(r["regs"])} · {_pct(r["share"])}</text>',
        ]
    parts.append("</svg>")
    return "\n".join(parts)


def build(conn: sqlite3.Connection, out_dir: str | Path = "report", focus: tuple[str, ...] = FOCUS_MAKES) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    last = max(years(conn))
    mark = _year

    lines = [f"# Neuzulassungen in Österreich {min(years(conn))}–{last}", ""]
    lines += ["## Markt nach Antrieb", "",
              "| Jahr | Pkw gesamt | davon E-Autos | E-Anteil | Plug-in-Hybrid | Vollhybrid |",
              "|---|---:|---:|---:|---:|---:|"]
    for r in market_overview(conn):
        lines.append(f"| {mark(r['year'])} | {_fmt(r['total'])} | {_fmt(r['bev'])} | {_pct(r['bev_share'])} "
                     f"| {_pct(r['phev_share'])} | {_pct(r['hev_share'])} |")

    lines += ["", f"## Fokusmarken: {', '.join(_brand(m) for m in focus)}", "",
              "| Marke | Jahr | Zulassungen | Wachstum ggü. Vorjahr | davon E-Autos | E-Anteil |",
              "|---|---|---:|---:|---:|---:|"]
    for r in brand_trend(conn, focus):
        growth = "–" if r["growth"] is None else f"{r['growth']:+.0f} %"
        lines.append(f"| {_brand(r['make'])} | {mark(r['year'])} | {_fmt(r['regs'])} | {growth} | {_fmt(r['bev'])} "
                     f"| {_pct(r['bev_share'])} |")

    ranking = brand_ranking(conn, last, "BEV", 10)
    svg = ranking_svg(ranking, focus, f"E-Auto-Neuzulassungen {mark(last)}: Top 10 Marken")
    (out / "bev_ranking.svg").write_text(svg, encoding="utf-8")
    lines += ["", f"## E-Autos {mark(last)}: Top 10 Marken", "", "![Top 10 E-Auto-Marken](bev_ranking.svg)", "",
              f"## E-Autos {mark(last)}: Top 10 Modelle", "", "| Marke | Modell | Zulassungen | Verbrauch Wh/km |",
              "|---|---|---:|---:|"]
    for r in top_models(conn, last, "BEV", limit=10):
        lines.append(f"| {_brand(r['make'])} | {r['model']} | {_fmt(r['regs'])} | {_fmt(r['wh_per_km'])} |")

    lines += ["", "\\* vorläufige Daten der EEA.", "",
              "Quelle: European Environment Agency (EEA), Monitoring of CO₂ emissions from passenger cars "
              "(Verordnung (EU) 2019/631), abgerufen über DiscoData. Weiterverwendung mit Quellenangabe."]
    path = out / "marktbericht.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
