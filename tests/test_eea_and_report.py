import asyncio

import httpx
import pytest

from automarkt import eea, mcp_server
from automarkt.report import build


@pytest.mark.parametrize(("raw", "clean"), [
    ("MITSUBISHI MOTORS THAILAND", "MITSUBISHI"),
    ("Mitsubishi Motors Corporation", "MITSUBISHI"),
    ("MERCEDS-AMG", "MERCEDES-AMG"),
    ("MERCEDES AMG", "MERCEDES-AMG"),
    ("VOLKSWAGEN, VW", "VOLKSWAGEN"),
    ("  byd ", "BYD"),
    ("MGA", "MGA"),  # only the brand MG, not every name starting with the letters
    ("TESLA", "TESLA"),
])
def test_clean_make(raw, clean):
    assert eea.clean_make(raw) == clean


def test_clean_model_drops_repeated_make():
    assert eea.clean_model("BYD  SEALION 7", "BYD") == "SEALION 7"
    assert eea.clean_model("MG4 ELECTRIC", "MG") == "MG4 ELECTRIC"


def test_merge_adds_up_normalised_duplicates():
    rows = [
        eea._row({"Year": 2025, "Mk": "BYD", "Cn": "Seal", "Ft": "ELECTRIC", "Fm": "e", "regs": 3, "whkm": 180}),
        eea._row({"Year": 2025, "Mk": "byd ", "Cn": "SEAL", "Ft": "electric", "Fm": "E", "regs": 1, "whkm": 200}),
    ]
    (merged,) = eea.merge(rows)
    assert (merged["make"], merged["model"], merged["regs"]) == ("BYD", "SEAL", 4)
    assert merged["whkm"] == pytest.approx(185)  # weighted by registrations
    assert merged["co2"] is None


def test_fetch_year_pages_through_results(monkeypatch):
    monkeypatch.setattr(eea, "PAGE_SIZE", 2)
    pages = {1: [{"Year": 2025, "Mk": "BYD", "Cn": f"M{i}", "Ft": "electric", "Fm": "E", "regs": 1} for i in range(2)],
             2: [{"Year": 2025, "Mk": "MG", "Cn": "MG4", "Ft": "electric", "Fm": "E", "regs": 5}]}
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.params)
        return httpx.Response(200, json={"results": pages[int(request.url.params["p"])]})

    rows = eea.fetch_year(2025, client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert len(rows) == 3 and len(seen) == 2
    assert "co2cars_2025Pv31" in seen[0]["query"] and "MS = 'AT'" in seen[0]["query"]


def test_api_error_is_raised(monkeypatch):
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"errors": ["bad"]})))
    with pytest.raises(RuntimeError):
        eea.fetch_year(2024, client=client)


def test_report_files(conn, tmp_path):
    path = build(conn, tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "| BYD | 2025* | 3.600 | +100 % | 2.100 | 58,3 % |" in text  # 2025 is provisional
    assert "| Hyundai | 2024 |" in text
    svg = (tmp_path / "bev_ranking.svg").read_text(encoding="utf-8")
    assert svg.count("<rect") == 4 and "prefers-color-scheme: dark" in svg


def test_mcp_tools(conn, monkeypatch):
    monkeypatch.setattr(mcp_server, "_conn", conn)
    names = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert names == {"market_overview", "brand_trend", "brand_ranking", "top_models"}
    assert mcp_server.brand_ranking(2025, "bev")[0]["make"] == "TESLA"
    assert mcp_server.brand_trend(["byd"])[1]["growth"] == 100.0
