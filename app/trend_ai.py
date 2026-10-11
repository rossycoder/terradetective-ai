"""Trend detective: statistics + AI narrative over NASA POWER time series.

Pipeline:
  1. Annual means from monthly data (real NASA POWER values).
  2. Linear trend (least squares) -> warming/cooling rate per decade.
  3. Anomaly detection: years > 2 std dev from detrended baseline.
  4. AI narrative: heuristic detective report (default, offline, free) or
     a free-tier LLM (Groq/Gemini via app/free_llm.py) when a key is set.
Every narrative is labeled with its provider. No invented numbers.
"""
import math
import os

from app import free_llm

AI_PROVIDER = os.environ.get("AI_PROVIDER", "heuristic")  # heuristic | auto | groq | gemini


def annual_means(monthly: dict) -> dict:
    """monthly: {yyyymm: value} -> {year: mean}. Skips fill values (-999)."""
    years = {}
    for ym, v in monthly.items():
        if v is None or v == -999 or v < -900:
            continue
        y = int(str(ym)[:4])
        years.setdefault(y, []).append(v)
    return {y: sum(v) / len(v) for y, v in sorted(years.items()) if len(v) >= 6}


def linear_trend(annual: dict) -> dict:
    """Least-squares fit. Returns slope per year, per decade, R^2, n."""
    xs = sorted(annual.keys())
    n = len(xs)
    if n < 5:
        return {"slope_per_year": 0.0, "slope_per_decade": 0.0, "r2": 0.0, "n": n}
    x0 = xs[0]
    x = [k - x0 for k in xs]
    y = [annual[k] for k in xs]
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((xi - mx) ** 2 for xi in x)
    sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    slope = sxy / sxx if sxx else 0.0
    intercept = my - slope * mx
    ss_tot = sum((yi - my) ** 2 for yi in y)
    ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))
    r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
    return {"slope_per_year": slope, "slope_per_decade": slope * 10,
            "r2": r2, "n": n, "first_year": xs[0], "last_year": xs[-1]}


def detect_anomalies(annual: dict, trend: dict, sigma: float = 2.0) -> list:
    """Years whose residual (after removing trend) exceeds sigma * std."""
    xs = sorted(annual.keys())
    n = len(xs)
    if n < 5:
        return []
    x0 = xs[0]
    slope = trend["slope_per_year"]
    # intercept from means
    x = [k - x0 for k in xs]
    y = [annual[k] for k in xs]
    mx, my = sum(x) / n, sum(y) / n
    intercept = my - slope * mx
    resid = [yi - (slope * xi + intercept) for xi, yi in zip(x, y)]
    mean_r = sum(resid) / n
    std_r = math.sqrt(sum((r - mean_r) ** 2 for r in resid) / n)
    out = []
    for k, r in zip(xs, resid):
        if std_r and abs(r - mean_r) > sigma * std_r:
            out.append({"year": k, "anomaly": round(r - mean_r, 2),
                        "value": round(annual[k], 2)})
    return sorted(out, key=lambda d: abs(d["anomaly"]), reverse=True)


def heuristic_report(place: str, lat: float, lon: float,
                     t_trend: dict, p_trend: dict,
                     t_anom: list, p_anom: list) -> str:
    """Plain-language detective report from real statistics. Provider: heuristic."""
    lines = [f"DETECTIVE REPORT — {place} ({lat:.2f}, {lon:.2f})",
             f"Data: NASA POWER (MERRA-2), {t_trend.get('first_year')}-{t_trend.get('last_year')} "
             f"({t_trend.get('n')} years of monthly observations).", ""]
    # Temperature verdict
    s = t_trend["slope_per_decade"]
    if abs(s) < 0.05:
        lines.append(f"TEMPERATURE: No clear trend ({s:+.2f} °C/decade, R²={t_trend['r2']:.2f}). "
                     "The signal is flat — nothing to report here, detective.")
    else:
        direction = "warming" if s > 0 else "cooling"
        strength = "strong" if t_trend["r2"] > 0.5 else "moderate" if t_trend["r2"] > 0.25 else "weak but present"
        lines.append(f"TEMPERATURE: {direction.upper()} at {s:+.2f} °C per decade "
                     f"({strength} signal, R²={t_trend['r2']:.2f}). "
                     f"Over {t_trend['n']} years that compounds to roughly {s * t_trend['n'] / 10:+.1f} °C.")
    # Precipitation verdict
    ps = p_trend["slope_per_decade"]
    if abs(ps) < 0.02:
        lines.append(f"RAINFALL: Stable ({ps:+.3f} mm/day per decade).")
    else:
        d = "wetter" if ps > 0 else "drier"
        lines.append(f"RAINFALL: Getting {d} ({ps:+.3f} mm/day per decade, R²={p_trend['r2']:.2f}).")
    # Anomalies
    if t_anom:
        top = t_anom[0]
        lines.append(f"SMOKING GUN: {top['year']} stands out — "
                     f"{top['anomaly']:+.2f} °C off the trend line "
                     f"(annual mean {top['value']} °C). Worth investigating what happened that year.")
    if p_anom:
        top = p_anom[0]
        lines.append(f"RAINFALL OUTLIER: {top['year']} ({top['anomaly']:+.2f} mm/day off trend).")
    if not t_anom and not p_anom:
        lines.append("No extreme outlier years detected — change here is gradual, not spiky.")
    lines.append("")
    lines.append("METHOD: least-squares trend + ±2σ anomaly scan on NASA POWER monthly data. "
                 "Not a forecast — a reading of what already happened.")
    return "\n".join(lines)


def llm_report(prompt: str) -> tuple[str, str]:
    """Free-tier LLM narrative. Returns (narrative, provider_label).

    Raises RuntimeError when no key is configured or the call fails —
    build_report() catches it and falls back honestly to heuristic.
    """
    if AI_PROVIDER == "groq" and not os.environ.get("GROQ_API_KEY"):
        raise RuntimeError("AI_PROVIDER=groq but GROQ_API_KEY is not set.")
    if AI_PROVIDER == "gemini" and not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("AI_PROVIDER=gemini but GEMINI_API_KEY is not set.")
    text, label = free_llm.chat(
        "You are a climate data detective. Write a vivid 150-word detective-style "
        "report from the statistics given. Never invent numbers — use only the ones provided.",
        prompt, max_tokens=400, temperature=0.7)
    if text is None:
        raise RuntimeError(label)
    return text, label


def build_report(place, lat, lon, t_trend, p_trend, t_anom, p_anom) -> dict:
    stats_prompt = heuristic_report(place, lat, lon, t_trend, p_trend, t_anom, p_anom)
    provider = "heuristic"
    narrative = stats_prompt
    if AI_PROVIDER != "heuristic":
        try:
            narrative, provider = llm_report(stats_prompt)
        except Exception as e:
            narrative = stats_prompt + f"\n\n[LLM unavailable ({e}); heuristic report shown.]"
    return {"narrative": narrative, "provider": provider}
