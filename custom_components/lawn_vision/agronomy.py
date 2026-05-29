"""Pure agronomic helpers: Grünlandtemperatursumme (GTS) and Growing Degree Days (GDD)."""

from __future__ import annotations

from datetime import date
from typing import Iterable

from .const import GRASS_COOL_SEASON, GRASS_WARM_SEASON

GTS_THRESHOLD_K = 200
GDD_BASE_COOL_C = 5.5
GDD_BASE_WARM_C = 10.0


def gts_weight(month: int) -> float:
    """Return the DWD monthly weight for the Grünlandtemperatursumme."""
    if month == 1:
        return 0.5
    if month == 2:
        return 0.75
    return 1.0


def gdd_base_temp(grass_type: str) -> float:
    """Return the GDD base temperature for the configured grass type."""
    if grass_type == GRASS_WARM_SEASON:
        return GDD_BASE_WARM_C
    return GDD_BASE_COOL_C


def gts_day(t_mean_c: float | None, month: int) -> float:
    """Return the daily GTS contribution: positive mean temperature × monthly weight."""
    if t_mean_c is None:
        return 0.0
    return max(0.0, float(t_mean_c)) * gts_weight(month)


def gdd_day(t_mean_c: float | None, grass_type: str) -> float:
    """Return the daily GDD contribution: max(0, T_mean − base)."""
    if t_mean_c is None:
        return 0.0
    return max(0.0, float(t_mean_c) - gdd_base_temp(grass_type))


def accumulate_gts(daily_means: Iterable[tuple[date, float | None]]) -> float:
    """Sum daily GTS contributions across the provided (date, mean) pairs."""
    return sum(gts_day(temp, day.month) for day, temp in daily_means)


def accumulate_gdd(
    daily_means: Iterable[tuple[date, float | None]], grass_type: str
) -> float:
    """Sum daily GDD contributions across the provided (date, mean) pairs."""
    return sum(gdd_day(temp, grass_type) for _day, temp in daily_means)


def year_bounds(today: date) -> tuple[date, date]:
    """Return (January 1st of today's year, today) for accumulator coverage."""
    return date(today.year, 1, 1), today


def vegetation_started(gts_value: float | None) -> bool:
    """Return True when the accumulated GTS crosses the DWD 200 K threshold."""
    if gts_value is None:
        return False
    return gts_value >= GTS_THRESHOLD_K


def merge_daily_means(
    archive: Iterable[tuple[date, float | None]],
    recent: Iterable[tuple[date, float | None]],
) -> list[tuple[date, float | None]]:
    """Merge archive + recent daily means, preferring recent on date overlap.

    Recent is treated as fresher because the Open-Meteo archive endpoint lags
    real time by roughly five days; the forecast endpoint's ``past_days``
    response fills that gap. Both inputs are expected to be sorted by date,
    but the result re-sorts defensively.
    """
    merged: dict[date, float | None] = {}
    for day, temp in archive:
        merged[day] = temp
    for day, temp in recent:
        merged[day] = temp
    return sorted(merged.items(), key=lambda item: item[0])
