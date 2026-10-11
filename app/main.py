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

from .nasa_power import fetch_monthly
from .trend_ai import annual_means, linear_trend, detect_anomalies, build_report, AI_PROVIDER

app = FastAPI(title="TerraDetective AI")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


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
    return {"service": "TerraDetective AI", "nasa_source": "POWER API (MERRA-2)",
            "ai_provider": AI_PROVIDER, "nasa_key_required": False}


@app.post("/api/investigate")
def investigate(req: InvestigateRequest):
    if not (-90 <= req.lat <= 90 and -180 <= req.lon <= 180):
        raise HTTPException(400, "lat must be -90..90, lon -180..180")
    if req.end_year - req.start_year < 10:
        raise HTTPException(400, "Need at least 10 years of data for a trend.")
    try:
        raw = fetch_monthly(req.lat, req.lon, req.start_year, req.end_year)
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
        "data_source": "NASA POWER (MERRA-2 reanalysis), real observations",
        "temperature": {
            "annual_means_c": {str(k): round(v, 2) for k, v in t_ann.items()},
            "trend": {k: round(v, 4) if isinstance(v, float) else v for k, v in t_trend.items()},
            "anomalies": t_anom,
        },
        "precipitation": {
            "annual_means_mm_day": {str(k): round(v, 3) for k, v in p_ann.items()},
            "trend": {k: round(v, 5) if isinstance(v, float) else v for k, v in p_trend.items()},
            "anomalies": p_anom,
        },
        "report": report,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8125")))
