"""Persistent daily-mean-temperature history for GTS/GDD accumulators."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .weather_source import fetch_open_meteo_archive, fetch_open_meteo_past

LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY_TEMPLATE = "lawn_vision.{entry_id}.history"

# Open-Meteo's archive endpoint lags real time by ~5 days. The forecast
# endpoint with past_days fills that gap.
ARCHIVE_LAG_DAYS = 5
RECENT_WINDOW_DAYS = 10


class TemperatureHistoryStore:
    """Persist current-year daily mean temperatures in HA's storage."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialise the store for a specific config entry."""
        self._store: Store = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_TEMPLATE.format(entry_id=entry_id)
        )

    async def async_load(self) -> dict[str, Any]:
        """Return the stored payload or an empty default."""
        data = await self._store.async_load()
        if not isinstance(data, dict):
            return {"year": None, "daily_means": [], "source": None}
        return data

    async def async_save(
        self,
        year: int,
        daily_means: list[tuple[date, float | None]],
        source: str | None,
    ) -> None:
        """Persist the year's daily means as ISO-keyed entries."""
        payload = {
            "year": year,
            "daily_means": [
                {"day": day.isoformat(), "t_mean_c": temp}
                for day, temp in daily_means
            ],
            "source": source,
        }
        await self._store.async_save(payload)


def decode_daily_means(
    payload: dict[str, Any] | None,
) -> list[tuple[date, float | None]]:
    """Convert the stored JSON shape back to (date, mean) pairs (pure)."""
    if not isinstance(payload, dict):
        return []
    items = payload.get("daily_means") or []
    result: list[tuple[date, float | None]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        iso = item.get("day")
        raw = item.get("t_mean_c")
        try:
            day = date.fromisoformat(str(iso))
        except (TypeError, ValueError):
            continue
        try:
            value = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            value = None
        result.append((day, value))
    result.sort(key=lambda pair: pair[0])
    return result


async def bootstrap_history(
    hass: HomeAssistant,
    latitude: float,
    longitude: float,
    today: date,
) -> tuple[list[tuple[date, float | None]], str]:
    """Fetch a full year's daily means via archive + recent forecast hybrid.

    Returns the merged daily means and a short source tag describing which
    Open-Meteo endpoints actually contributed data.
    """
    from .agronomy import merge_daily_means

    year_start = date(today.year, 1, 1)
    archive_end = today - timedelta(days=ARCHIVE_LAG_DAYS)

    archive_pairs: list[tuple[date, float | None]] = []
    if archive_end >= year_start:
        archive_pairs = await fetch_open_meteo_archive(
            hass, latitude, longitude, year_start, archive_end
        )

    recent_window = max(RECENT_WINDOW_DAYS, ARCHIVE_LAG_DAYS + 2)
    recent_pairs = await fetch_open_meteo_past(
        hass, latitude, longitude, recent_window
    )
    # Restrict recent pairs to current year and up to today to avoid noise.
    recent_pairs = [
        (day, temp)
        for day, temp in recent_pairs
        if day.year == today.year and day <= today
    ]

    merged = merge_daily_means(archive_pairs, recent_pairs)

    if archive_pairs and recent_pairs:
        source = "open_meteo_archive+forecast"
    elif archive_pairs:
        source = "open_meteo_archive"
    elif recent_pairs:
        source = "open_meteo_forecast"
    else:
        source = "unavailable"
    return merged, source


async def refresh_recent(
    hass: HomeAssistant,
    latitude: float,
    longitude: float,
    existing: list[tuple[date, float | None]],
    today: date,
) -> tuple[list[tuple[date, float | None]], bool]:
    """Top up the trailing window with fresh Open-Meteo forecast data.

    Returns the merged list and a flag indicating whether anything changed.
    """
    from .agronomy import merge_daily_means

    recent_pairs = await fetch_open_meteo_past(
        hass, latitude, longitude, RECENT_WINDOW_DAYS
    )
    recent_pairs = [
        (day, temp)
        for day, temp in recent_pairs
        if day.year == today.year and day <= today
    ]
    if not recent_pairs:
        return existing, False
    merged = merge_daily_means(existing, recent_pairs)
    return merged, merged != existing
