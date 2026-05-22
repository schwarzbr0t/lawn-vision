"""Pure helper functions shared by coordinator, actions and forecast logic."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .translations import DEFAULT_LANGUAGE, WEEKDAY_NAMES, _t


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)


def _round_or_none(value: float | None, digits: int) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _average(values) -> float | None:
    numbers = [value for value in values if value is not None]
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


def _forecast_number(
    item: dict[str, Any], key: str, fallback: float | None = None
) -> float | None:
    try:
        value = item.get(key, fallback)
        if value in (None, "unknown", "unavailable"):
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _forecast_day_temperature(item: dict[str, Any]) -> float | None:
    high = _forecast_number(item, "temperature")
    low = _forecast_number(item, "templow")
    if high is not None and low is not None:
        return (high + low) / 2
    return high


def _forecast_rain_risk(items: list[dict[str, Any]]) -> float:
    probabilities = [
        _forecast_number(item, "precipitation_probability", 0) or 0 for item in items
    ]
    precipitation = [
        _forecast_number(item, "precipitation", 0) or 0 for item in items
    ]
    probability_risk = max(probabilities, default=0)
    precipitation_risk = min(sum(precipitation) * 18, 100)
    return _clamp(max(probability_risk, precipitation_risk), 0, 100)


def _format_forecast_time(value: Any, lang: str = DEFAULT_LANGUAGE) -> str:
    if not value:
        return _t(lang, "soon")
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return _t(lang, "soon")
    weekday = WEEKDAY_NAMES.get(lang, WEEKDAY_NAMES[DEFAULT_LANGUAGE])[parsed.weekday()]
    return f"{weekday} {parsed.strftime('%H:%M')}"
