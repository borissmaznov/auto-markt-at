import pytest

from automarkt.db import connect, load


def row(year, make, model, fuel, mode, regs, whkm=None):
    return {"year": year, "make": make, "model": model, "fuel": fuel, "fuel_mode": mode, "regs": regs,
            "co2": 0 if fuel == "electric" else 120, "kw": 100, "kg": 1600, "whkm": whkm}


# Small, hand-checked market: two years, focus makes plus Tesla and Volkswagen.
ROWS = [
    row(2024, "TESLA", "MODEL Y", "electric", "E", 5000, 150),
    row(2024, "BYD", "SEAL U", "electric", "E", 1000, 200),
    row(2024, "BYD", "SEAL U DM-I", "petrol/electric", "P", 800),
    row(2024, "MG", "MG4", "electric", "E", 1500, 170),
    row(2024, "HYUNDAI", "KONA", "electric", "E", 2000, 150),
    row(2024, "HYUNDAI", "TUCSON", "petrol/electric", "H", 3000),
    row(2024, "VOLKSWAGEN", "GOLF", "petrol", "M", 6000),
    row(2024, "MITSUBISHI", "SPACE STAR", "petrol", "M", 1500),
    row(2025, "TESLA", "MODEL Y", "electric", "E", 4000, 150),
    row(2025, "BYD", "SEALION 7", "electric", "E", 2100, 216),
    row(2025, "BYD", "SEAL U DM-I", "petrol/electric", "P", 1500),
    row(2025, "MG", "MG4", "electric", "E", 1200, 170),
    row(2025, "HYUNDAI", "KONA", "electric", "E", 2500, 150),
    row(2025, "HYUNDAI", "TUCSON", "petrol/electric", "H", 3500),
    row(2025, "VOLKSWAGEN", "GOLF", "petrol", "M", 5000),
    row(2025, "MITSUBISHI", "SPACE STAR", "petrol", "M", 1000),
]


@pytest.fixture
def conn():
    c = connect(":memory:")
    load(c, ROWS)
    yield c
    c.close()
