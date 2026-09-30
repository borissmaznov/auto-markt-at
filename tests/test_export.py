import csv

from automarkt.export import export_star


def read(path):
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_star_schema_files(conn, tmp_path):
    counts = export_star(conn, tmp_path)
    assert counts == {"fact_registrations": 16, "dim_make": 6, "dim_year": 2, "dim_drive": 4}

    facts = read(tmp_path / "fact_registrations.csv")
    assert sum(int(r["regs"]) for r in facts) == 20800 * 2  # same totals as the database
    assert {r["drive"] for r in facts} == {"BEV", "PHEV", "HEV", "ICE"}
    assert facts[0]["consumption_wh_km"] == "200.0"  # BYD SEAL U 2024, empty for combustion cars
    assert next(r for r in facts if r["model"] == "GOLF")["consumption_wh_km"] == ""


def test_dimensions_for_filters(conn, tmp_path):
    export_star(conn, tmp_path)
    makes = {r["make"]: r for r in read(tmp_path / "dim_make.csv")}
    assert (makes["BYD"]["brand"], makes["BYD"]["focus_brand"]) == ("BYD", "1")
    assert (makes["HYUNDAI"]["brand"], makes["TESLA"]["focus_brand"]) == ("Hyundai", "0")
    years = {r["year"]: r for r in read(tmp_path / "dim_year.csv")}
    assert (years["2025"]["label"], years["2025"]["provisional"]) == ("2025*", "1")
    assert years["2024"]["provisional"] == "0"
