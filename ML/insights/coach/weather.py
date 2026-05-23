"""Open-Meteo client for Malaysian cities. Free, no API key.

Docs: https://open-meteo.com/en/docs

We use only forecast + current temperature. One HTTP call per location, cached
to disk for the rest of the hour. The coach engine reads from the cache; never
hits the network on a hot demo path.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CACHE_DIR = Path(__file__).resolve().parent / "_weather_cache"
CACHE_TTL_SECONDS = 60 * 60        # 1 hour
USER_AGENT = "WattsEye/0.1 (hackathon prototype; contact: choongzhuolin@gmail.com)"

# Malaysian city coordinates — extend as needed
CITIES: dict[str, tuple[float, float]] = {
    "Kuala Lumpur": (3.139, 101.687),
    "Petaling Jaya": (3.107, 101.607),
    "Shah Alam": (3.073, 101.518),
    "George Town": (5.414, 100.329),
    "Johor Bahru": (1.493, 103.741),
    "Ipoh": (4.598, 101.090),
    "Kuching": (1.553, 110.359),
    "Kota Kinabalu": (5.978, 116.073),
    "Melaka": (2.196, 102.250),
}


@dataclass(frozen=True)
class WeatherForecast:
    city: str
    current_temp_c: float
    today_max_c: float
    daily_max_c: list[float]            # next 7 days
    hot_days_over_33c: int
    fetched_at: datetime
    source: str = "open-meteo"


def _cache_path(city: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = city.lower().replace(" ", "_")
    return CACHE_DIR / f"{safe}.json"


def _read_cache(city: str) -> dict[str, Any] | None:
    path = _cache_path(city)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if time.time() - data["_cached_at"] < CACHE_TTL_SECONDS:
            return data
    except (OSError, json.JSONDecodeError, KeyError):
        return None
    return None


def _write_cache(city: str, payload: dict[str, Any]) -> None:
    payload["_cached_at"] = time.time()
    _cache_path(city).write_text(json.dumps(payload))


def _fetch(lat: float, lon: float) -> dict[str, Any]:
    params = urlencode({
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m",
        "daily": "temperature_2m_max",
        "timezone": "Asia/Kuala_Lumpur",
        "forecast_days": 7,
    })
    url = f"https://api.open-meteo.com/v1/forecast?{params}"
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def get_forecast(city: str = "Kuala Lumpur", hot_threshold_c: float = 33.0) -> WeatherForecast:
    """Return current + 7-day forecast for a Malaysian city. Cached for 1 hour."""
    if city not in CITIES:
        raise ValueError(f"Unknown city: {city}. Known: {list(CITIES)}")

    cached = _read_cache(city)
    if cached is None:
        lat, lon = CITIES[city]
        raw = _fetch(lat, lon)
        _write_cache(city, raw)
        cached = raw

    current_temp = float(cached["current"]["temperature_2m"])
    daily_max = [float(t) for t in cached["daily"]["temperature_2m_max"]]
    return WeatherForecast(
        city=city,
        current_temp_c=current_temp,
        today_max_c=daily_max[0] if daily_max else current_temp,
        daily_max_c=daily_max,
        hot_days_over_33c=sum(1 for t in daily_max if t > hot_threshold_c),
        fetched_at=datetime.now(timezone.utc),
    )


def get_forecast_safe(city: str = "Kuala Lumpur") -> WeatherForecast | None:
    """Like get_forecast but returns None on network failure instead of raising.

    Use this from the coach engine so that an offline Pi doesn't break the demo.
    """
    try:
        return get_forecast(city)
    except Exception:
        return None


if __name__ == "__main__":
    fc = get_forecast("Kuala Lumpur")
    print(f"{fc.city}: current {fc.current_temp_c:.1f}°C, today max {fc.today_max_c:.1f}°C")
    print(f"7-day max: {[round(t, 1) for t in fc.daily_max_c]}")
    print(f"Hot days (>33°C): {fc.hot_days_over_33c}")
