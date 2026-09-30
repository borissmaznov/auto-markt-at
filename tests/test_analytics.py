import pytest

from automarkt import analytics


def test_market_overview(conn):
    y2024, y2025 = analytics.market_overview(conn)
    assert (y2024["total"], y2024["bev"], y2024["bev_share"], y2024["phev_share"]) == (20800, 9500, 45.7, 3.8)
    assert (y2025["bev"], y2025["bev_share"], y2025["phev_share"]) == (9800, 47.1, 7.2)


def test_brand_trend_growth_uses_previous_year(conn):
    trend = {(r["make"], r["year"]): r for r in analytics.brand_trend(conn)}
    assert trend[("BYD", 2024)]["growth"] is None  # no earlier year in the data
    assert trend[("BYD", 2025)]["regs"] == 3600
    assert trend[("BYD", 2025)]["growth"] == 100.0
    assert trend[("BYD", 2025)]["bev_share"] == 58.3
    assert trend[("MG", 2025)]["growth"] == -20.0
    assert ("TESLA", 2025) not in trend  # only the focus makes


def test_brand_ranking_with_market_share(conn):
    ranking = analytics.brand_ranking(conn, 2025, "BEV")
    assert [(r["rank"], r["make"], r["share"]) for r in ranking] == [
        (1, "TESLA", 40.8), (2, "HYUNDAI", 25.5), (3, "BYD", 21.4), (4, "MG", 12.2)]


def test_top_models_by_drive_and_make(conn):
    models = analytics.top_models(conn, 2025, "BEV")
    assert [m["model"] for m in models] == ["MODEL Y", "KONA", "SEALION 7", "MG4"]
    byd = analytics.top_models(conn, 2025, "PHEV", make="byd")
    assert [(m["model"], m["regs"]) for m in byd] == [("SEAL U DM-I", 1500)]


@pytest.mark.parametrize(("fuel", "mode", "drive"), [
    ("electric", "E", "BEV"), ("petrol/electric", "P", "PHEV"), ("petrol/electric", "H", "HEV"),
    ("petrol", "H", "HEV"),  # EEA reports many full hybrids as petrol with fuel mode H
    ("diesel", "M", "ICE"),
])
def test_drive_type_view(conn, fuel, mode, drive):
    got = conn.execute("SELECT drive FROM registrations_typed WHERE fuel = ? AND fuel_mode = ? LIMIT 1",
                       (fuel, mode)).fetchone()
    if got is None:  # diesel is not in the fixture: check the rule directly
        conn.execute("INSERT INTO registrations VALUES (2025, 'X', 'Y', ?, ?, 1, 0, 0, 0, NULL)", (fuel, mode))
        got = conn.execute("SELECT drive FROM registrations_typed WHERE make = 'X'").fetchone()
    assert got["drive"] == drive
