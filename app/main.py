"""TerraDetective AI — Earth System Trend Detective for NASA Space Apps 2026.

Challenge: "Be an Earth System Trend Detective"
Theme: The Next Frontier | Event: Nov 14-15, 2026 (virtual Universal Event)

Flow: pick a place -> real NASA POWER data (40 years) -> trend + anomaly AI
      -> detective report + charts.
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .nasa_power import fetch_monthly, fetch_daily_tmax, cache_stats
from .trend_ai import annual_means, linear_trend, detect_anomalies, build_report, AI_PROVIDER
from .twin_cities import find_twin
from . import free_llm

app = FastAPI(title="TerraDetective AI")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


def _round_trend(tr: dict) -> dict:
    """Round trend stats for JSON; keeps CI lists and p-value readable."""
    out = {}
    for k, v in tr.items():
        if k == "p_value" and isinstance(v, float):
            out[k] = round(v, 6)
        elif isinstance(v, float):
            out[k] = round(v, 4)
        elif isinstance(v, list):
            out[k] = [round(x, 4) if isinstance(x, float) else x for x in v]
        else:
            out[k] = v
    return out


class InvestigateRequest(BaseModel):
    place: str = "Karachi, Pakistan"
    lat: float = 24.86
    lon: float = 67.01
    start_year: int = 1985
    end_year: int = 2025


@app.get("/")
def index():
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))


@app.get("/api/status")
def status():
    return {"service": "TerraDetective AI", "nasa_source": "POWER API (MERRA-2 reanalysis)",
            "ai_provider": AI_PROVIDER, "nasa_key_required": False,
            "cache": cache_stats()}


@app.post("/api/investigate")
def investigate(req: InvestigateRequest):
    if not (-90 <= req.lat <= 90 and -180 <= req.lon <= 180):
        raise HTTPException(400, "lat must be -90..90, lon -180..180")
    if req.end_year - req.start_year < 10:
        raise HTTPException(400, "Need at least 10 years of data for a trend.")
    try:
        raw, cached = fetch_monthly(req.lat, req.lon, req.start_year, req.end_year)
    except Exception as e:
        raise HTTPException(502, f"NASA POWER API error: {e}")
    t_ann = annual_means(raw["t2m"])
    p_ann = annual_means(raw["prec"])
    t_trend = linear_trend(t_ann)
    p_trend = linear_trend(p_ann)
    t_anom = detect_anomalies(t_ann, t_trend)
    p_anom = detect_anomalies(p_ann, p_trend)
    report = build_report(req.place, req.lat, req.lon, t_trend, p_trend, t_anom, p_anom)
    return {
        "place": req.place, "lat": req.lat, "lon": req.lon,
        "elevation_m": raw["elevation_m"],
        "cached": cached,
        "data_source": "NASA POWER (MERRA-2 reanalysis), real observations",
        "temperature": {
            "annual_means_c": {str(k): round(v, 2) for k, v in t_ann.items()},
            "trend": _round_trend(t_trend),
            "anomalies": t_anom,
        },
        "precipitation": {
            "annual_means_mm_day": {str(k): round(v, 3) for k, v in p_ann.items()},
            "trend": _round_trend(p_trend),
            "anomalies": p_anom,
        },
        "report": report,
    }


class NarrateRequest(BaseModel):
    place: str = "Karachi, Pakistan"
    stats_text: str = ""  # the heuristic report text to narrate


@app.post("/api/narrate")
def narrate(req: NarrateRequest):
    """Real AI narration of the detective report (Pollinations -> Groq -> Gemini).
    Honest: returns provider label, or an explicit failure so the UI keeps
    the heuristic report instead of faking AI output."""
    if not req.stats_text.strip():
        raise HTTPException(400, "stats_text is required.")
    text, label = free_llm.chat(
        "You are a climate data detective. Write a vivid 150-word detective-style "
        "report from the statistics given. Never invent numbers — use only the ones provided. "
        "Keep the tone noir-detective, first person.",
        f"Case location: {req.place}\n\nEvidence:\n{req.stats_text[:3000]}",
        max_tokens=450, temperature=0.75)
    if text is None:
        raise HTTPException(503, f"AI narration unavailable: {label}")
    return {"narrative": text, "provider": label}


class TwinCityRequest(BaseModel):
    place: str = "Karachi, Pakistan"
    lat: float = 24.86
    lon: float = 67.01
    start_year: int = 1985
    end_year: int = 2025


@app.post("/api/twin-city")
def twin_city(req: TwinCityRequest):
    """Future Twin City: extrapolate the measured warming trend to 2050 and
    find the nearest present-day city by annual mean temperature."""
    if not (-90 <= req.lat <= 90 and -180 <= req.lon <= 180):
        raise HTTPException(400, "lat must be -90..90, lon -180..180")
    try:
        raw, cached = fetch_monthly(req.lat, req.lon, req.start_year, req.end_year)
    except Exception as e:
        raise HTTPException(502, f"NASA POWER API error: {e}")
    t_ann = annual_means(raw["t2m"])
    if len(t_ann) < 5:
        raise HTTPException(502, "Not enough NASA data for this location.")
    t_trend = linear_trend(t_ann)
    last_year = max(t_ann.keys())
    result = find_twin(req.place, last_year, t_ann[last_year],
                       t_trend["slope_per_year"])
    result["data_source"] = "NASA POWER (MERRA-2), real observations"
    result["cached"] = cached
    return result


class NormalCheckRequest(BaseModel):
    place: str = "Karachi, Pakistan"
    lat: float = 24.86
    lon: float = 67.01
    year: int | None = None    # if None: auto-pick most extreme recent month
    month: int | None = None
    start_year: int = 1985
    end_year: int = 2025


@app.post("/api/normal-check")
def normal_check(req: NormalCheckRequest):
    """Was This Normal? Compare one month against its own 40-year baseline."""
    if not (-90 <= req.lat <= 90 and -180 <= req.lon <= 180):
        raise HTTPException(400, "lat must be -90..90, lon -180..180")
    try:
        raw, cached = fetch_monthly(req.lat, req.lon, req.start_year, req.end_year)
    except Exception as e:
        raise HTTPException(502, f"NASA POWER API error: {e}")
    # Organize by month: {mm: [(yyyymm, val)]}
    by_month: dict[int, list[tuple[int, float]]] = {}
    for ym, v in raw["t2m"].items():
        if v is None or v < -900:
            continue
        ymi = int(ym)
        y, m = ymi // 100, ymi % 100
        by_month.setdefault(m, []).append((ymi, v))
    if req.year and req.month:
        target_ym = req.year * 100 + req.month
    else:
        # Auto: most extreme month (by |z|) in the last 3 years
        recent_cut = (req.end_year - 2) * 100
        best = None
        for m, obs in by_month.items():
            vals = [v for _, v in obs]
            if len(vals) < 10:
                continue
            mean = sum(vals) / len(vals)
            var = sum((v - mean) ** 2 for v in vals) / len(vals)
            std = var ** 0.5
            for ymi, v in obs:
                if ymi < recent_cut:
                    continue
                z = abs((v - mean) / std) if std else 0.0
                if best is None or z > best[0]:
                    best = (z, ymi, m)
        if best is None:
            raise HTTPException(502, "Not enough NASA data for this location.")
        target_ym = best[1]
    ty, tm = target_ym // 100, target_ym % 100
    obs = by_month.get(tm, [])
    vals = sorted(v for _, v in obs)
    target_val = next((v for ymi, v in obs if ymi == target_ym), None)
    if target_val is None or len(vals) < 10:
        raise HTTPException(404, "That month is not in the NASA record for this location.")
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    std = var ** 0.5
    z = (target_val - mean) / std if std else 0.0
    # Percentile + "1-in-N" among the n same-month observations
    rank = sum(1 for v in vals if v <= target_val)  # 1..n
    n = len(vals)
    obs_years = [ymi // 100 for ymi, _ in obs]
    rank_from_top = n - rank + 1
    one_in_n = round(n / rank_from_top) if rank_from_top else n
    percentile = round(rank / n * 100, 1)
    if abs(z) >= 2:
        verdict, emoji = "NOT NORMAL", "🔴"
    elif abs(z) >= 1:
        verdict, emoji = "UNUSUAL", "🟡"
    else:
        verdict, emoji = "NORMAL", "🟢"
    month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return {
        "place": req.place, "lat": req.lat, "lon": req.lon,
        "year": ty, "month": tm, "month_name": month_names[tm],
        "observed_c": round(target_val, 2),
        "baseline_mean_c": round(mean, 2),
        "baseline_std_c": round(std, 2),
        "anomaly_c": round(target_val - mean, 2),
        "z_score": round(z, 2),
        "percentile": percentile,
        "one_in_n_years": one_in_n,
        "baseline_years": n,
        "baseline_first_year": min(obs_years),
        "baseline_last_year": max(obs_years),
        "verdict": verdict, "emoji": emoji,
        "cached": cached,
        "data_source": "NASA POWER (MERRA-2) monthly T2M, real observations",
    }


class DangerDaysRequest(BaseModel):
    place: str = "Karachi, Pakistan"
    lat: float = 24.86
    lon: float = 67.01
    threshold_c: float = 35.0
    start_year: int = 1985
    end_year: int = 2025


@app.post("/api/danger-days")
def danger_days(req: DangerDaysRequest):
    """Danger Days: count days/year with T2M_MAX >= threshold, per-decade bars."""
    if not (-90 <= req.lat <= 90 and -180 <= req.lon <= 180):
        raise HTTPException(400, "lat must be -90..90, lon -180..180")
    if not (30 <= req.threshold_c <= 50):
        raise HTTPException(400, "threshold_c must be 30..50")
    try:
        raw, cached = fetch_daily_tmax(req.lat, req.lon, req.start_year, req.end_year)
    except Exception as e:
        raise HTTPException(502, f"NASA POWER API error: {e}")
    per_year: dict[int, int] = {}
    per_year_total: dict[int, int] = {}
    for day, v in raw["daily"].items():
        if v is None or v < -900:
            continue
        y = int(str(day)[:4])
        per_year_total[y] = per_year_total.get(y, 0) + 1
        if v >= req.threshold_c:
            per_year[y] = per_year.get(y, 0) + 1
    years = sorted(per_year_total.keys())
    # Per-decade buckets (calendar decades), marking partial coverage
    decades: dict[str, list[int]] = {}
    for y in years:
        label = f"{y // 10 * 10}s"
        decades.setdefault(label, []).append(y)
    decade_bars = []
    for label in sorted(decades.keys()):
        ys = decades[label]
        full = [y for y in ys if per_year_total.get(y, 0) >= 360]
        if not full:
            continue
        avg = sum(per_year.get(y, 0) for y in full) / len(full)
        decade_bars.append({
            "decade": label,
            "avg_days_per_year": round(avg, 1),
            "years_covered": len(full),
            "partial": len(full) < 10,
        })
    first_avg = decade_bars[0]["avg_days_per_year"] if decade_bars else 0
    last_avg = decade_bars[-1]["avg_days_per_year"] if decade_bars else 0
    return {
        "place": req.place, "lat": req.lat, "lon": req.lon,
        "threshold_c": req.threshold_c,
        "cached": cached,
        "first_year": years[0] if years else None,
        "last_year": years[-1] if years else None,
        "per_year": {str(y): per_year.get(y, 0) for y in years},
        "decades": decade_bars,
        "first_decade_avg": first_avg,
        "last_decade_avg": last_avg,
        "change_per_year": round(last_avg - first_avg, 1),
        "data_source": "NASA POWER (MERRA-2) daily T2M_MAX, real observations",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8125")))
