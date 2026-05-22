"""Weather adapter: Open-Meteo (free, no API key).

Open-Meteo aggregates data from DWD/ICON among other models and is the
fastest path for German users who do not have a weather entity wired up.
Attribution: https://open-meteo.com/
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import aiohttp

from homeassistant.helpers.aiohttp_client import async_get_clientsession

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_TIMEOUT_SECONDS = 15

OPEN_METEO_PARAMS = {
    "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,soil_temperature_18cm,soil_moisture_9_27cm",
    "hourly": "temperature_2m,precipitation,precipitation_probability,weather_code",
    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code",
    "timezone": "auto",
    "forecast_days": 14,
}

WEATHER_CODE_MAP: dict[int, str] = {
    0: "sunny",
    1: "partlycloudy",
    2: "partlycloudy",
    3: "cloudy",
    45: "fog",
    48: "fog",
    51: "rainy",
    53: "rainy",
    55: "rainy",
    56: "rainy",
    57: "rainy",
    61: "rainy",
    63: "rainy",
    65: "pouring",
    66: "rainy",
    67: "pouring",
    71: "snowy",
    73: "snowy",
    75: "snowy",
    77: "snowy",
    80: "rainy",
    81: "pouring",
    82: "pouring",
    85: "snowy",
    86: "snowy",
    95: "lightning",
    96: "lightning-rainy",
    99: "lightning-rainy",
}


async def fetch_open_meteo(
    hass: "HomeAssistant", latitude: float, longitude: float
) -> dict[str, Any] | None:
    """Fetch current + forecast data from Open-Meteo and map it to Lawn Vision shape."""
    params = {"latitude": latitude, "longitude": longitude, **OPEN_METEO_PARAMS}

    session = async_get_clientsession(hass)
    try:
        async with session.get(
            OPEN_METEO_URL,
            params=params,
            timeout=aiohttp.ClientTimeout(total=OPEN_METEO_TIMEOUT_SECONDS),
        ) as resp:
            if resp.status != 200:
                LOGGER.warning("Open-Meteo returned HTTP %s", resp.status)
                return None
            data = await resp.json()
    except (aiohttp.ClientError, TimeoutError) as err:
        LOGGER.warning("Open-Meteo fetch failed: %s", err)
        return None

    return map_open_meteo(data)


def map_open_meteo(data: dict[str, Any]) -> dict[str, Any]:
    """Convert an Open-Meteo response to Lawn Vision payload (pure)."""
    current = data.get("current") or {}
    hourly_raw = data.get("hourly") or {}
    daily_raw = data.get("daily") or {}

    hourly_items: list[dict[str, Any]] = []
    for index, ts in enumerate(hourly_raw.get("time") or []):
        hourly_items.append({
            "datetime": ts,
            "temperature": _at(hourly_raw, "temperature_2m", index),
            "precipitation": _at(hourly_raw, "precipitation", index) or 0,
            "precipitation_probability": _at(hourly_raw, "precipitation_probability", index) or 0,
            "condition": _weather_code_to_condition(_at(hourly_raw, "weather_code", index)),
        })

    daily_items: list[dict[str, Any]] = []
    for index, ts in enumerate(daily_raw.get("time") or []):
        daily_items.append({
            "datetime": ts,
            "temperature": _at(daily_raw, "temperature_2m_max", index),
            "templow": _at(daily_raw, "temperature_2m_min", index),
            "precipitation": _at(daily_raw, "precipitation_sum", index) or 0,
            "precipitation_probability": _at(daily_raw, "precipitation_probability_max", index) or 0,
            "condition": _weather_code_to_condition(_at(daily_raw, "weather_code", index)),
        })

    soil_moisture = current.get("soil_moisture_9_27cm")
    moisture_pct: float | None = None
    if isinstance(soil_moisture, (int, float)):
        moisture_pct = float(soil_moisture) * 100

    return {
        "current": {
            "temperature_c": current.get("temperature_2m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "rain_mm": current.get("precipitation"),
            "soil_temperature_c": current.get("soil_temperature_18cm"),
            "moisture_pct": moisture_pct,
            "condition": _weather_code_to_condition(current.get("weather_code")),
        },
        "forecast": {
            "hourly": hourly_items,
            "daily": daily_items,
        },
    }


def _at(payload: dict[str, Any], key: str, index: int) -> Any:
    values = payload.get(key) or []
    if 0 <= index < len(values):
        return values[index]
    return None


def _weather_code_to_condition(code: Any) -> str:
    try:
        return WEATHER_CODE_MAP.get(int(code), "")
    except (TypeError, ValueError):
        return ""
