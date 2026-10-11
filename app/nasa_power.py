"""NASA POWER API client — real, no-key Earth climate data.

POWER (Prediction Of Worldwide Energy Resources), NASA Langley.
Docs: https://power.larc.nasa.gov/docs/
Verified 2026-10-11: monthly endpoint works with start=YYYY&end=YYYY.
"""
import requests

BASE = "https://power.larc.nasa.gov/api"

# Parameters we use (POWER names):
# T2M = 2-meter air temperature (C), PRECTOTCORR = precipitation (mm/day)
PARAMS = "T2M,PRECTOTCORR"


def fetch_monthly(lat: float, lon: float, start_year: int = 1985, end_year: int = 2025,
                  timeout: int = 60) -> dict:
    """Fetch monthly T2M + precipitation for a point. Returns {t2m: {yyyymm: val}, prec: {...}}."""
    url = (f"{BASE}/temporal/monthly/point?parameters={PARAMS}&community=AG"
           f"&longitude={lon}&latitude={lat}&format=JSON"
           f"&start={start_year}&end={end_year}")
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if "properties" not in data:
        raise ValueError(f"POWER API error: {str(data)[:200]}")
    p = data["properties"]["parameter"]
    return {
        "t2m": {k: v for k, v in p["T2M"].items() if k != "ANN"},
        "prec": {k: v for k, v in p["PRECTOTCORR"].items() if k != "ANN"},
        "elevation_m": data["geometry"]["coordinates"][2],
    }


def fetch_climatology(lat: float, lon: float, timeout: int = 30) -> dict:
    """Long-term monthly climatology (baseline) for a point."""
    url = (f"{BASE}/temporal/climatology/point?parameters={PARAMS}&community=AG"
           f"&longitude={lon}&latitude={lat}&format=JSON")
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    p = data["properties"]["parameter"]
    return {
        "t2m": {k: v for k, v in p["T2M"].items() if k != "ANN"},
        "prec": {k: v for k, v in p["PRECTOTCORR"].items() if k != "ANN"},
    }
