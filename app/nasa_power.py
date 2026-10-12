"""NASA POWER API client — real, no-key Earth climate data.

POWER (Prediction Of Worldwide Energy Resources), NASA Langley.
Docs: https://power.larc.nasa.gov/docs/
Verified 2026-10-11: monthly endpoint works with start=YYYY&end=YYYY.

Caching: in-memory TTL cache keyed by (endpoint, rounded lat/lon, years)
so repeat investigations and Vercel warm instances skip the slow NASA
round-trip. A best-effort background thread pre-warms popular cities at
cold start (never blocks a request). Responses report "cached" honestly.
"""
import os
import threading
import time

import requests

BASE = "https://power.larc.nasa.gov/api"

# Parameters we use (POWER names):
# T2M = 2-meter air temperature (C), PRECTOTCORR = precipitation (mm/day)
PARAMS = "T2M,PRECTOTCORR"

# --- cache -----------------------------------------------------------------
_CACHE: dict = {}
_CACHE_TTL_S = 24 * 3600          # 1 day
_CACHE_MAX = 256                 # evict oldest beyond this


def _ckey(kind: str, lat: float, lon: float, start_year: int, end_year: int):
    return (kind, round(lat, 2), round(lon, 2), start_year, end_year)


def _cache_get(key):
    hit = _CACHE.get(key)
    if hit is None:
        return None
    ts, val = hit
    if time.time() - ts > _CACHE_TTL_S:
        _CACHE.pop(key, None)
        return None
    return val


def _cache_put(key, val):
    if len(_CACHE) >= _CACHE_MAX:
        # evict oldest (dicts preserve insertion order)
        _CACHE.pop(next(iter(_CACHE)), None)
    _CACHE[key] = (time.time(), val)


def cache_stats() -> dict:
    return {"entries": len(_CACHE), "ttl_hours": _CACHE_TTL_S // 3600,
            "max_entries": _CACHE_MAX}


def fetch_monthly(lat: float, lon: float, start_year: int = 1985, end_year: int = 2025,
                  timeout: int = 60) -> tuple[dict, bool]:
    """Fetch monthly T2M + precipitation. Returns (data, cached).

    data: {t2m: {yyyymm: val}, prec: {...}, elevation_m: ...}
    """
    key = _ckey("monthly", lat, lon, start_year, end_year)
    hit = _cache_get(key)
    if hit is not None:
        return hit, True
    url = (f"{BASE}/temporal/monthly/point?parameters={PARAMS}&community=AG"
           f"&longitude={lon}&latitude={lat}&format=JSON"
           f"&start={start_year}&end={end_year}")
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if "properties" not in data:
        raise ValueError(f"POWER API error: {str(data)[:200]}")
    p = data["properties"]["parameter"]
    result = {
        "t2m": {k: v for k, v in p["T2M"].items() if k != "ANN"},
        "prec": {k: v for k, v in p["PRECTOTCORR"].items() if k != "ANN"},
        "elevation_m": data["geometry"]["coordinates"][2],
    }
    _cache_put(key, result)
    return result, False


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


def fetch_daily_tmax(lat: float, lon: float, start_year: int = 1985,
                     end_year: int = 2025, timeout: int = 60) -> tuple[dict, bool]:
    """Fetch DAILY maximum 2m temperature (T2M_MAX). Returns (data, cached).

    data: {daily: {"YYYYMMDD": value}}. ~14,600 days for 40 years.
    Fill values (-999) are kept as-is for the caller to filter.
    """
    key = _ckey("daily_tmax", lat, lon, start_year, end_year)
    hit = _cache_get(key)
    if hit is not None:
        return hit, True
    url = (f"{BASE}/temporal/daily/point?parameters=T2M_MAX&community=AG"
           f"&longitude={lon}&latitude={lat}&format=JSON"
           f"&start={start_year}&end={end_year}")
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if "properties" not in data:
        raise ValueError(f"POWER API error: {str(data)[:200]}")
    p = data["properties"]["parameter"]
    result = {"daily": dict(p["T2M_MAX"])}
    _cache_put(key, result)
    return result, False


# --- popular-city pre-warm (best effort, never blocks) -----------------------
POPULAR_CITIES = [
    ("Karachi, Pakistan", 24.86, 67.01),
    ("Lahore, Pakistan", 31.55, 74.35),
    ("Delhi, India", 28.61, 77.21),
    ("Dhaka, Bangladesh", 23.81, 90.41),
    ("Riyadh, Saudi Arabia", 24.71, 46.68),
    ("London, UK", 51.50, -0.12),
]


def _warm_popular():
    """Fetch monthly data for popular cities in the background."""
    for _name, lat, lon in POPULAR_CITIES:
        try:
            fetch_monthly(lat, lon, 1985, 2025, timeout=45)
        except Exception:
            pass  # best effort only


if os.environ.get("TERRA_WARMUP", "1") == "1":
    try:
        threading.Thread(target=_warm_popular, daemon=True).start()
    except Exception:
        pass
