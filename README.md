# 🛰️ TerraDetective AI — Earth System Trend Detective

**NASA Space Apps Challenge 2026** · Theme: *The Next Frontier* · Nov 14–15, 2026 (virtual Universal Event)
Challenge: **"Be an Earth System Trend Detective"**

Pick any place on Earth → the app pulls **40 years of real NASA climate data** → AI finds the
trends and anomalies → you get a detective-style report on what changed and when.

## The story (problem → NASA data → AI → impact)

**Problem.** Climate change is abstract until you see it in *your* city. Farmers, city planners,
and students hear "global warming" but can't answer: *is MY place warming? How fast? When did it
start?* For a climate-vulnerable country like Pakistan, that answer shapes real decisions.

**NASA data.** NASA's POWER project (Prediction Of Worldwide Energy Resources, Langley Research
Center) serves 40+ years of MERRA-2 reanalysis — temperature and precipitation for any lat/lon on
Earth, free, no API key. We query it live.

**AI solution.** A trend-detective pipeline: least-squares warming-rate estimation (°C/decade),
±2σ anomaly detection for outlier years, and an AI-written detective narrative (heuristic by
default, upgradeable to an LLM). Interactive chart with fitted trend line.

**Impact.** Turns a global abstraction into a local, checkable fact — in under 60 seconds, in a
browser, for any place on Earth. A teacher in Karachi, a farmer in Thar, a student in London all
get their own evidence.

## Quickstart

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# optional: AI_PROVIDER=auto + GROQ_API_KEY for real-AI narratives (default is offline heuristic; see LLM_SETUP.md)
PORT=8125 python -m app.main
# open http://localhost:8125
```

Or with uvicorn directly: `uvicorn app.main:app --port 8125` (run from project root).

## Architecture

```
browser UI (static/index.html)
   │  POST /api/investigate {place, lat, lon, start_year, end_year}
   ▼
FastAPI (app/main.py)
   ├─ app/nasa_power.py  → NASA POWER API (live, no key)
   │    monthly T2M + PRECTOTCORR → annual means
   └─ app/trend_ai.py    → linear trend (°C/decade, R²)
                           ±2σ anomaly scan
                           detective narrative (heuristic | openai)
```

## API

- `GET /api/status` — service info, AI provider, key requirements
- `POST /api/investigate` — full analysis; needs ≥10 years of data

## Data sources (all real, verified 2026-10-11)

| Source | Use | Key needed |
|---|---|---|
| NASA POWER API (`power.larc.nasa.gov`) — MERRA-2 | temperature + precipitation time series | No |
| api.nasa.gov (APOD, etc.) | bonus imagery endpoints | Free key or DEMO_KEY |

No fake data anywhere: if NASA is unreachable the API returns 502, never invented numbers.

## What's real vs stubbed

| Component | Status |
|---|---|
| NASA POWER live data | ✅ real, tested |
| Trend + anomaly statistics | ✅ real (least squares, σ-scan) |
| Heuristic detective narrative | ✅ real, labeled provider |
| LLM narrative upgrade | optional, env-gated |
| Preset locations | real coordinates |

## Roadmap for the hackathon weekend

- [ ] Webhook-free share links (encode lat/lon in URL)
- [ ] Compare-two-places mode (e.g., Karachi vs London)
- [ ] PDF detective report export
- [ ] Urdu/Roman-Urdu narrative option
