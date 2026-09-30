"""Download aggregated new car registrations for Austria from the EEA DiscoData SQL API.

Source: European Environment Agency, "Monitoring of CO2 emissions from passenger cars" (Regulation (EU) 2019/631).
One row in the EEA tables is one registered car; we aggregate on the server by year, make, model and fuel.
"""

from __future__ import annotations

import logging
import re

import httpx

log = logging.getLogger(__name__)

API = "https://discodata.eea.europa.eu/sql"
PAGE_SIZE = 10_000

# Year -> (table, extra filter). The "latest" table holds final and provisional rows for older years,
# so 2021 is filtered to final data to avoid counting every car twice.
SOURCES: dict[int, tuple[str, str]] = {
    2021: ("co2cars", "AND Year = 2021 AND Status = 'F'"),
    2022: ("co2cars", "AND Year = 2022"),
    2023: ("co2cars_2023Fv28", ""),
    2024: ("co2cars_2024Fv30", ""),
    2025: ("co2cars_2025Pv31", ""),
}
PROVISIONAL = {2022, 2025}  # only provisional EEA data published so far

QUERY = (
    "SELECT Year, Mk, Cn, Ft, Fm, SUM(r) AS regs, AVG([Ewltp (g/km)]) AS co2, AVG([Ep (KW)]) AS kw, "
    "AVG([M (kg)]) AS kg, AVG([Z (Wh/km)]) AS whkm "
    "FROM [CO2Emission].[latest].[{table}] WHERE MS = '{country}' {where} "
    "GROUP BY Year, Mk, Cn, Ft, Fm"
)


# The same make is reported under several names ("MITSUBISHI MOTORS THAILAND", "MERCEDS-AMG" ...).
MAKE_RULES = [
    (re.compile(r"^MITSUBISHI\b"), "MITSUBISHI"),
    (re.compile(r"^HYUNDAI\b"), "HYUNDAI"),
    (re.compile(r"^BYD\b"), "BYD"),
    (re.compile(r"^(SAIC )?MG\b"), "MG"),
    (re.compile(r"^MERCEDE?S[ -]AMG\b"), "MERCEDES-AMG"),
    (re.compile(r"^(VOLKSWAGEN|VW)\b"), "VOLKSWAGEN"),
]


def clean_make(raw: str) -> str:
    make = re.sub(r"\s+", " ", raw.strip().upper())
    for pattern, name in MAKE_RULES:
        if pattern.search(make):
            return name
    return make


def clean_model(raw: str, make: str) -> str:
    model = re.sub(r"\s+", " ", raw.strip().upper())
    return model[len(make) + 1:] if model.startswith(make + " ") else model  # "BYD SEALION 7" -> "SEALION 7"


def _row(r: dict) -> dict:
    make = clean_make(str(r.get("Mk") or ""))
    return {
        "year": int(r["Year"]),
        "make": make,
        "model": clean_model(str(r.get("Cn") or ""), make),
        "fuel": str(r.get("Ft") or "").strip().lower(),
        "fuel_mode": str(r.get("Fm") or "").strip().upper(),
        "regs": int(r.get("regs") or 0),
        "co2": r.get("co2"),
        "kw": r.get("kw"),
        "kg": r.get("kg"),
        "whkm": r.get("whkm"),
    }


KEY_FIELDS = ("year", "make", "model", "fuel", "fuel_mode")
METRICS = ("co2", "kw", "kg", "whkm")


def merge(rows: list[dict]) -> list[dict]:
    """After normalising names two EEA groups can share a key ("BYD" and "Byd "): add them up,
    averages weighted by registrations."""
    merged: dict[tuple, dict] = {}
    metrics = METRICS
    for r in rows:
        key = tuple(r[k] for k in KEY_FIELDS)
        m = merged.setdefault(key, {**dict(zip(KEY_FIELDS, key, strict=True)), "regs": 0,
                                    **{f"_{x}": [0.0, 0] for x in metrics}})
        m["regs"] += r["regs"]
        for x in metrics:
            if r[x] is not None and r["regs"]:
                m[f"_{x}"][0] += r[x] * r["regs"]
                m[f"_{x}"][1] += r["regs"]
    out = []
    for m in merged.values():
        for x in metrics:
            total, weight = m.pop(f"_{x}")
            m[x] = total / weight if weight else None
        out.append(m)
    return out


def fetch_year(year: int, country: str = "AT", client: httpx.Client | None = None) -> list[dict]:
    table, where = SOURCES[year]
    sql = QUERY.format(table=table, country=country, where=where)
    http = client or httpx.Client(timeout=120)
    rows: list[dict] = []
    page = 1
    while True:
        resp = http.get(API, params={"query": sql, "p": page, "nrOfHits": PAGE_SIZE})
        resp.raise_for_status()
        body = resp.json()
        if "errors" in body:
            raise RuntimeError(f"EEA API error for {year}: {body['errors']}")
        batch = body.get("results", [])
        rows += [_row(r) for r in batch]
        if len(batch) < PAGE_SIZE:
            return merge(rows)
        page += 1


def fetch_all(years=SOURCES, country: str = "AT", client: httpx.Client | None = None) -> list[dict]:
    rows: list[dict] = []
    for year in years:
        log.info("fetching %s", year)
        rows += fetch_year(year, country, client)
    return rows
