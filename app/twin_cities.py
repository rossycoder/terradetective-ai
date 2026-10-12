"""Future Twin City — "what will my city feel like in 2050?"

Extrapolates the measured warming trend to 2050 and matches the projected
annual mean temperature against a small built-in database of world cities'
*current* annual mean temperatures. Illustrative, honestly labeled —
not a climate-model projection.
"""
import math

# Approximate current annual mean 2m temperatures (°C), well-known climatology.
# Used only to find the nearest present-day "twin". Kept small on purpose.
REFERENCE_CITIES = [
    ("Dubai, UAE", 28.0),
    ("Jakarta, Indonesia", 28.1),
    ("Bangkok, Thailand", 29.1),
    ("Singapore", 27.9),
    ("Lagos, Nigeria", 27.3),
    ("Mumbai, India", 27.2),
    ("Karachi, Pakistan", 26.5),
    ("Riyadh, Saudi Arabia", 26.3),
    ("Delhi, India", 25.3),
    ("Miami, USA", 25.1),
    ("Phoenix, USA", 23.9),
    ("Cairo, Egypt", 22.6),
    ("Houston, USA", 21.4),
    ("Nairobi, Kenya", 19.0),
    ("São Paulo, Brazil", 19.6),
    ("Lima, Peru", 19.4),
    ("Sydney, Australia", 18.7),
    ("Athens, Greece", 18.3),
    ("Buenos Aires, Argentina", 17.9),
    ("Tehran, Iran", 17.7),
    ("Mexico City, Mexico", 16.6),
    ("Tokyo, Japan", 16.3),
    ("Addis Ababa, Ethiopia", 16.4),
    ("Madrid, Spain", 15.1),
    ("Istanbul, Türkiye", 14.9),
    ("Bogotá, Colombia", 14.5),
    ("New York, USA", 13.3),
    ("Beijing, China", 12.9),
    ("Paris, France", 12.3),
    ("London, UK", 11.3),
    ("Chicago, USA", 10.3),
    ("Moscow, Russia", 6.3),
]


def find_twin(place: str, last_year: int, last_mean_c: float,
              slope_per_year: float, target_year: int = 2050) -> dict:
    """Project to target_year and find the nearest reference city."""
    years_ahead = target_year - last_year
    projected = last_mean_c + slope_per_year * years_ahead
    # Never match the place with itself — skip the DB entry whose city token
    # equals the investigated place's city token.
    own = place.split(",")[0].strip().lower()
    cands = [c for c in REFERENCE_CITIES
             if c[0].split(",")[0].strip().lower() != own] or REFERENCE_CITIES
    ranked = sorted(cands, key=lambda c: abs(c[1] - projected))
    best, runner_up = ranked[0], ranked[1] if len(ranked) > 1 else ranked[0]
    return {
        "place": place,
        "target_year": target_year,
        "last_year": last_year,
        "last_annual_mean_c": round(last_mean_c, 2),
        "slope_per_year": round(slope_per_year, 5),
        "projected_mean_c": round(projected, 2),
        "warming_by_target_c": round(projected - last_mean_c, 2),
        "twin_city": best[0],
        "twin_city_mean_c": best[1],
        "twin_delta_c": round(projected - best[1], 2),
        "runner_up": runner_up[0],
        "method": ("linear extrapolation of measured trend — illustrative, "
                   "not a climate-model projection"),
    }
