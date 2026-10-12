# 🛰️ TerraDetective AI — Earth System Trend Detective

**NASA Space Apps Challenge 2026** · Theme: *The Next Frontier* · Nov 14–15, 2026 (virtual Universal Event)
Challenge: **"Be an Earth System Trend Detective"**

🌍 **Live demo:** https://terradetective-ai.vercel.app

Pick any place on Earth → the app pulls **40 years of real NASA climate data** → AI finds the
trends and anomalies → you get a detective-style report on what changed and when.

## The story (problem → NASA data → AI → impact)

**Problem.** Climate change is abstract until you see it in *your* city. Farmers, city planners,
and students hear "global warming" but can't answer: *is MY place warming? How fast? Was that
heatwave normal?* For a climate-vulnerable country like Pakistan, those answers shape real decisions.

**NASA data.** NASA's POWER project (Prediction Of Worldwide Energy Resources, Langley Research
Center) serves 40+ years of temperature and precipitation for any lat/lon on Earth, free, no API
key. We query it live.

**AI solution.** A trend-detective pipeline: least-squares warming-rate estimation (°C/decade) with
a **95% confidence interval and p-value**, ±2σ anomaly detection for outlier years, and an
AI-written detective narrative (heuristic by default, upgradeable to a free-tier LLM — always
labeled with its provider). Interactive charts, a 2050 "twin city" reveal, anomaly verdicts, and
danger-day counts.

**Impact.** Turns a global abstraction into a local, checkable fact — in under 60 seconds, in a
browser, for any place on Earth. A teacher in Karachi, a farmer in Thar, a student in London all
get their own evidence.

## Features

| # | Feature | What it does |
|---|---|---|
| 1 | 🔍 40-year investigation | Warming/cooling trend (°C/decade), 95% CI + p-value, R² fit, anomaly years, interactive chart |
| 2 | 🔮 Future Twin City | Extrapolates your measured trend to 2050 and reveals which present-day city you'll feel like (e.g. Karachi 2050 ≈ today's Riyadh) |
| 3 | 🌡️ Was This Normal? | Pick any month — get a verdict (NOT NORMAL / UNUSUAL / NORMAL) with z-score, percentile and "1-in-N-year" rarity vs its own 40-year baseline |
| 4 | ☠️ Danger Days | Counts days/year above 35 °C from real daily NASA data, decade-by-decade bars |
| 5 | ✨ Narrate with AI | A real LLM narrates your detective report (Pollinations → Groq → Gemini); provider always labeled, honest fallback when unavailable |
| 6 | 🗺️ Map picker | Click anywhere on the world map to investigate that exact spot |
| 7 | 🔗 Share links | Every case gets a shareable URL (`?place=&lat=&lon=`) that re-runs the analysis on open |
| 8 | ⚡ Smart caching | NASA responses cached server-side (24 h TTL); popular cities pre-warmed so first loads are fast |
| 9 | ⬇️ Case-file download | Export the full investigation as a Markdown dossier |

## Data honesty

- **MERRA-2 reanalysis data** — POWER serves model-assimilated reanalysis, not direct thermometer
  observations. We say so wherever the source is shown, because judges (and users) deserve honesty.
- **No fake data anywhere:** if NASA is unreachable the API returns **502**, never invented numbers.
- Twin City is an illustrative extrapolation of the measured trend, labeled as such — not a
  climate-model projection.

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
browser UI (static/index.html) — Leaflet map picker, charts, share links
   │  POST /api/investigate {place, lat, lon, start_year, end_year}
   │  POST /api/twin-city | /api/normal-check | /api/danger-days | /api/narrate
   ▼
FastAPI (app/main.py)
   ├─ app/nasa_power.py  → NASA POWER API (live, no key) + 24h TTL cache + popular-city pre-warm
   ├─ app/trend_ai.py    → linear trend (°C/decade, 95% CI, p-value, R²)
   │                        ±2σ anomaly scan
   │                        detective narrative (heuristic | LLM, provider-labeled)
   └─ app/twin_cities.py → 2050 projection matched against reference-city climatology
```

## API

- `GET /api/status` — service info, AI provider, cache stats, key requirements
- `POST /api/investigate` — full analysis; needs ≥10 years of data; returns `cached: true/false`
- `POST /api/twin-city` — Future Twin City reveal
- `POST /api/normal-check` — Was This Normal? verdict (explicit or auto-picked extreme month)
- `POST /api/danger-days` — dangerous-heat-day counts per decade (daily T2M_MAX)
- `POST /api/narrate` — real-AI narration of a report (503 with honest reason when unavailable)

## Data sources (all real, verified 2026-10-11)

| Source | Use | Key needed |
|---|---|---|
| NASA POWER API (`power.larc.nasa.gov`) — MERRA-2 reanalysis | temperature + precipitation time series | No |
| Pollinations / Groq / Gemini (free tiers) | optional AI narration | Only if you enable it |

## What's real vs stubbed

| Component | Status |
|---|---|
| NASA POWER live data | ✅ real, tested |
| Trend + 95% CI + p-value statistics | ✅ real (least squares, Student-t, pure Python — verified against scipy) |
| Anomaly detection (±2σ) | ✅ real |
| Twin City / Was This Normal? / Danger Days | ✅ real |
| Heuristic detective narrative | ✅ real, labeled provider |
| LLM narrative upgrade | optional, env-gated, labeled |
| Map picker, share links, caching | ✅ real |
| Preset locations | real coordinates |

## Roadmap (honest next steps)

- [x] Share links (encode lat/lon in URL) — done
- [x] Compare-two-places mode — done as **Future Twin City**
- [ ] PDF detective report export (Markdown case file already ships)
- [ ] Roman-Urdu narrative option
- [ ] Season-shift detection (earlier summers, changing rainfall patterns)
- [ ] NASA GIBS satellite imagery layer

## License

MIT — see [LICENSE](LICENSE). Built for NASA Space Apps 2026 by Rozeena.
