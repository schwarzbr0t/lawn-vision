"""Care action heuristics and seven-day plan for Lawn Vision.

This module owns:
- The seasonal/cooldown windows for each care action.
- Per-action decision heuristics (mow/water/fertilize/scarify/aerate/overseed).
- Conflict resolution between competing recommendations.
- The "next action" headline and the 7-day care plan.

It is intentionally pure: no Home Assistant or coordinator state lives here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from .const import (
    ACTION_AERATE,
    ACTION_FERTILIZE,
    ACTION_LAST_DONE_KEYS,
    ACTION_MOW,
    ACTION_OVERSEED,
    ACTION_SCARIFY,
    ACTION_SENSOR_KEYS,
    ACTION_STATE_DO_NOW,
    ACTION_STATE_OFF_SEASON,
    ACTION_STATE_SKIP,
    ACTION_STATE_SOON,
    ACTION_STATE_WAIT,
    ACTION_WATER,
    CARE_ACTIONS,
    GRASS_COOL_SEASON,
    GRASS_WARM_SEASON,
)
from .helpers import (
    _average,
    _clamp,
    _forecast_day_temperature,
    _forecast_number,
    _forecast_rain_risk,
    _format_forecast_time,
    _round_or_none,
)
from .translations import DEFAULT_LANGUAGE, MONTH_NAMES, WEEKDAY_NAMES, _t

if TYPE_CHECKING:
    from .coordinator import LawnInputs


SEASONAL_WINDOWS_COOL: dict[str, tuple[tuple[int, int], ...]] = {
    ACTION_FERTILIZE: ((3, 9),),
    ACTION_SCARIFY: ((4, 5), (9, 9)),
    ACTION_AERATE: ((4, 5), (9, 10)),
    ACTION_OVERSEED: ((4, 5), (8, 9)),
}
SEASONAL_WINDOWS_WARM: dict[str, tuple[tuple[int, int], ...]] = {
    ACTION_FERTILIZE: ((4, 10),),
    ACTION_SCARIFY: ((5, 6),),
    ACTION_AERATE: ((5, 6),),
    ACTION_OVERSEED: ((5, 6),),
}

ACTION_COOLDOWN_DAYS: dict[str, int] = {
    ACTION_MOW: 7,
    ACTION_WATER: 3,
    ACTION_FERTILIZE: 42,
    ACTION_SCARIFY: 180,
    ACTION_AERATE: 300,
    ACTION_OVERSEED: 60,
}

NEXT_ACTION_PRIORITY: tuple[str, ...] = (
    ACTION_WATER,
    ACTION_MOW,
    ACTION_FERTILIZE,
    ACTION_OVERSEED,
    ACTION_SCARIFY,
    ACTION_AERATE,
)



def _care_actions(
    *,
    inputs: LawnInputs,
    forecast: dict[str, list[dict[str, Any]]],
    last_done: dict[str, str | None],
    now: datetime,
    growth: float,
    mowing: float,
    stress: float,
    phase: str,
    water_need: float,
    moisture: float | None,
    soil_temp: float | None,
    rain_risk_24h: float,
    lang: str = DEFAULT_LANGUAGE,
) -> dict[str, dict[str, Any]]:
    """Compute per-action care recommendations."""
    hourly = forecast.get("hourly") or []
    daily = forecast.get("daily") or []
    rain_24h_mm = sum(
        _forecast_number(item, "precipitation", 0) or 0
        for item in (hourly[:24] or daily[:1])
    )
    rain_48h_mm = sum(
        _forecast_number(item, "precipitation", 0) or 0
        for item in (hourly[:48] or daily[:2])
    )
    month = now.month
    windows = (
        SEASONAL_WINDOWS_WARM
        if inputs.grass_type == GRASS_WARM_SEASON
        else SEASONAL_WINDOWS_COOL
    )

    days = {
        action: _days_since_state(last_done.get(action), now) for action in CARE_ACTIONS
    }

    actions = {
        ACTION_MOW: _action_mow(
            growth, mowing, stress, phase, rain_risk_24h, rain_24h_mm,
            days[ACTION_MOW], hourly, lang,
        ),
        ACTION_WATER: _action_water(
            water_need, phase, rain_48h_mm, rain_risk_24h, days[ACTION_WATER], lang,
        ),
        ACTION_FERTILIZE: _action_fertilize(
            phase, soil_temp, stress, month, windows, days[ACTION_FERTILIZE], lang,
        ),
        ACTION_SCARIFY: _action_scarify(
            growth, soil_temp, phase, stress, month, windows, rain_24h_mm,
            rain_risk_24h, days[ACTION_SCARIFY], lang,
        ),
        ACTION_AERATE: _action_aerate(
            moisture, soil_temp, phase, month, windows, days[ACTION_AERATE], lang,
        ),
        ACTION_OVERSEED: _action_overseed(
            soil_temp, stress, month, windows, daily, days[ACTION_OVERSEED], lang,
        ),
    }
    return _resolve_conflicts(actions, last_done, lang)


ANNUAL_ACTIONS: tuple[str, ...] = (ACTION_SCARIFY, ACTION_AERATE, ACTION_OVERSEED)


def _resolve_conflicts(
    actions: dict[str, dict[str, Any]],
    last_done: dict[str, str | None],
    lang: str = DEFAULT_LANGUAGE,
) -> dict[str, dict[str, Any]]:
    """Apply pragmatic sequencing rules so the user does not see five 'do now' items.

    - Annual actions (scarify/aerate/overseed) without a tracking helper get
      capped at 'soon' so a fresh install does not push major work on day one.
    - Scarify dominates the pflege round: if it is do_now, fertilize and aerate
      are sequenced afterwards.
    """
    for action in ANNUAL_ACTIONS:
        if (
            last_done.get(action) is None
            and actions[action]["state"] == ACTION_STATE_DO_NOW
        ):
            actions[action] = {
                **actions[action],
                "state": ACTION_STATE_SOON,
                "reason": (
                    actions[action].get("reason", "")
                    + _t(lang, "conflict.annual_track")
                ),
                "reason_code": "needs_tracking_helper",
            }

    if actions[ACTION_SCARIFY]["state"] == ACTION_STATE_DO_NOW:
        if actions[ACTION_FERTILIZE]["state"] == ACTION_STATE_DO_NOW:
            actions[ACTION_FERTILIZE] = {
                **actions[ACTION_FERTILIZE],
                "state": ACTION_STATE_SOON,
                "next_window": _t(lang, "conflict.fert_after_scarify_next"),
                "next_window_code": "after_scarify_2_3_days",
                "reason": _t(lang, "conflict.fert_after_scarify_reason"),
                "reason_code": "fert_after_scarify",
            }
        if actions[ACTION_AERATE]["state"] == ACTION_STATE_DO_NOW:
            actions[ACTION_AERATE] = {
                **actions[ACTION_AERATE],
                "state": ACTION_STATE_SOON,
                "next_window": _t(lang, "conflict.aerate_skip_scarify_next"),
                "next_window_code": "other_round",
                "reason": _t(lang, "conflict.aerate_skip_scarify_reason"),
                "reason_code": "aerate_skip_scarify_round",
            }

    if (
        actions[ACTION_OVERSEED]["state"] == ACTION_STATE_DO_NOW
        and actions[ACTION_FERTILIZE]["state"] == ACTION_STATE_DO_NOW
    ):
        actions[ACTION_FERTILIZE] = {
            **actions[ACTION_FERTILIZE],
            "reason": (
                actions[ACTION_FERTILIZE].get("reason", "")
                + _t(lang, "conflict.overseed_starter_hint")
            ),
            "reason_code": "use_starter_fertilizer",
        }

    return actions


def _action_mow(
    growth: float,
    mowing: float,
    stress: float,
    phase: str,
    rain_risk: float,
    rain_24h_mm: float,
    days_since: int | None,
    hourly: list[dict[str, Any]],
    lang: str = DEFAULT_LANGUAGE,
) -> dict[str, Any]:
    cooldown = ACTION_COOLDOWN_DAYS[ACTION_MOW]
    if phase == "dormant":
        return _result(
            ACTION_STATE_SKIP, _t(lang, "next_window.dash"), _t(lang, "mow.skip_dormant"),
            days_since, cooldown, reason_code="skip_dormant", next_window_code="dash",
        )
    if stress >= 65:
        return _result(
            ACTION_STATE_SKIP, _t(lang, "mow.skip_stress_next"), _t(lang, "mow.skip_stress"),
            days_since, cooldown, reason_code="skip_stress", next_window_code="after_recovery",
        )
    if days_since is not None and days_since < 3:
        return _result(
            ACTION_STATE_WAIT,
            _t(lang, "mow.wait_recent_next", days=3 - days_since),
            _t(lang, "mow.wait_recent", days=days_since),
            days_since,
            cooldown,
            reason_code="wait_recent",
            next_window_code="wait_days",
        )
    if mowing >= 65 and growth >= 55 and rain_risk < 60 and rain_24h_mm < 2:
        return _result(
            ACTION_STATE_DO_NOW, _t(lang, "mow.do_now_next"), _t(lang, "mow.do_now"),
            days_since, cooldown, reason_code="do_now", next_window_code="today",
        )
    if mowing >= 45:
        window = _next_dry_window(hourly, lang) or _t(lang, "soon")
        return _result(
            ACTION_STATE_SOON, window, _t(lang, "mow.soon"),
            days_since, cooldown, reason_code="soon_dry_window", next_window_code="next_dry_window",
        )
    if rain_risk >= 60 or rain_24h_mm >= 2:
        return _result(
            ACTION_STATE_WAIT, _t(lang, "mow.wait_rain_next"), _t(lang, "mow.wait_rain"),
            days_since, cooldown, reason_code="wait_rain", next_window_code="after_rain",
        )
    return _result(
        ACTION_STATE_WAIT, _t(lang, "mow.wait_growth_next"), _t(lang, "mow.wait_growth"),
        days_since, cooldown, reason_code="wait_growth", next_window_code="observe",
    )


def _action_water(
    water_need: float,
    phase: str,
    rain_48h_mm: float,
    rain_risk: float,
    days_since: int | None,
    lang: str = DEFAULT_LANGUAGE,
) -> dict[str, Any]:
    cooldown = ACTION_COOLDOWN_DAYS[ACTION_WATER]
    if phase == "dormant":
        return _result(
            ACTION_STATE_SKIP, _t(lang, "next_window.dash"), _t(lang, "water.skip_dormant"),
            days_since, cooldown, reason_code="skip_dormant", next_window_code="dash",
        )
    if days_since is not None and days_since < 1:
        return _result(
            ACTION_STATE_WAIT, _t(lang, "water.wait_recent_next"), _t(lang, "water.wait_recent"),
            days_since, cooldown, reason_code="wait_recent", next_window_code="tomorrow",
        )
    if rain_48h_mm >= 5 and water_need < 8:
        return _result(
            ACTION_STATE_WAIT,
            _t(lang, "water.wait_rain_next"),
            _t(lang, "water.wait_rain", mm=round(rain_48h_mm, 1)),
            days_since,
            cooldown,
            reason_code="wait_rain",
            next_window_code="after_rain",
        )
    if water_need >= 6 and rain_risk < 60:
        return _result(
            ACTION_STATE_DO_NOW, _t(lang, "water.do_now_next"), _t(lang, "water.do_now"),
            days_since, cooldown, reason_code="do_now", next_window_code="this_evening",
        )
    if water_need >= 3:
        return _result(
            ACTION_STATE_SOON, _t(lang, "water.soon_next"), _t(lang, "water.soon"),
            days_since, cooldown, reason_code="soon", next_window_code="1_2_days",
        )
    return _result(
        ACTION_STATE_WAIT, _t(lang, "water.ok_next"), _t(lang, "water.ok"),
        days_since, cooldown, reason_code="ok", next_window_code="observe",
    )


def _action_fertilize(
    phase: str,
    soil_temp: float | None,
    stress: float,
    month: int,
    windows: dict[str, tuple[tuple[int, int], ...]],
    days_since: int | None,
    lang: str = DEFAULT_LANGUAGE,
) -> dict[str, Any]:
    cooldown = ACTION_COOLDOWN_DAYS[ACTION_FERTILIZE]
    win = windows.get(ACTION_FERTILIZE, ())
    if not _in_window(month, win):
        return _result(
            ACTION_STATE_OFF_SEASON, _next_window_label(month, win, lang), _t(lang, "fert.off_season"),
            days_since, cooldown, reason_code="off_season", next_window_code="next_season_month",
        )
    if phase == "dormant":
        return _result(
            ACTION_STATE_SKIP, _t(lang, "fert.skip_dormant_next"), _t(lang, "fert.skip_dormant"),
            days_since, cooldown, reason_code="skip_dormant", next_window_code="after_growth_start",
        )
    if stress >= 60:
        return _result(
            ACTION_STATE_SKIP, _t(lang, "fert.skip_stress_next"), _t(lang, "fert.skip_stress"),
            days_since, cooldown, reason_code="skip_stress", next_window_code="after_recovery",
        )
    if days_since is not None and days_since < cooldown:
        return _result(
            ACTION_STATE_WAIT,
            _t(lang, "fert.wait_cooldown_next", days=cooldown - days_since),
            _t(lang, "fert.wait_cooldown", days=days_since),
            days_since,
            cooldown,
            reason_code="wait_cooldown",
            next_window_code="wait_days",
        )
    if soil_temp is None:
        return _result(
            ACTION_STATE_SOON, _t(lang, "fert.soon_unknown_next"), _t(lang, "fert.soon_unknown"),
            days_since, cooldown, reason_code="soon_soil_unknown", next_window_code="when_soil_stable",
        )
    if soil_temp < 6:
        return _result(
            ACTION_STATE_WAIT,
            _t(lang, "fert.wait_cold_next"),
            _t(lang, "fert.wait_cold", temp=f"{soil_temp:.0f}"),
            days_since,
            cooldown,
            reason_code="wait_soil_cold",
            next_window_code="when_soil_warm",
        )
    if soil_temp < 8:
        return _result(
            ACTION_STATE_SOON,
            _t(lang, "fert.soon_warm_next"),
            _t(lang, "fert.soon_warm", temp=f"{soil_temp:.0f}"),
            days_since,
            cooldown,
            reason_code="soon_soil_warming",
            next_window_code="few_days",
        )
    if phase in ("waking_up", "active_growth"):
        hint = (
            _t(lang, "fert.do_now_unknown") if days_since is None
            else _t(lang, "fert.do_now_known", days=days_since)
        )
        return _result(
            ACTION_STATE_DO_NOW,
            _t(lang, "fert.do_now_next"),
            _t(lang, "fert.do_now", temp=f"{soil_temp:.0f}", hint=hint),
            days_since,
            cooldown,
            reason_code="do_now",
            next_window_code="today_tomorrow",
        )
    return _result(
        ACTION_STATE_SOON, _t(lang, "fert.wait_slow_next"), _t(lang, "fert.wait_slow"),
        days_since, cooldown, reason_code="soon_growth_slow", next_window_code="at_growth_spurt",
    )


def _action_scarify(
    growth: float,
    soil_temp: float | None,
    phase: str,
    stress: float,
    month: int,
    windows: dict[str, tuple[tuple[int, int], ...]],
    rain_24h_mm: float,
    rain_risk: float,
    days_since: int | None,
    lang: str = DEFAULT_LANGUAGE,
) -> dict[str, Any]:
    cooldown = ACTION_COOLDOWN_DAYS[ACTION_SCARIFY]
    win = windows.get(ACTION_SCARIFY, ())
    if not _in_window(month, win):
        return _result(
            ACTION_STATE_OFF_SEASON, _next_window_label(month, win, lang), _t(lang, "scarify.off_season"),
            days_since, cooldown, reason_code="off_season", next_window_code="next_season_month",
        )
    if phase == "dormant" or stress >= 60:
        return _result(
            ACTION_STATE_SKIP, _t(lang, "scarify.skip_stress_next"), _t(lang, "scarify.skip_stress"),
            days_since, cooldown, reason_code="skip_stress", next_window_code="after_recovery",
        )
    if days_since is not None and days_since < cooldown:
        return _result(
            ACTION_STATE_WAIT,
            _t(lang, "scarify.wait_cooldown_next"),
            _t(lang, "scarify.wait_cooldown", days=days_since),
            days_since,
            cooldown,
            reason_code="wait_cooldown",
            next_window_code="next_season",
        )
    if soil_temp is not None and soil_temp < 10:
        return _result(
            ACTION_STATE_SOON,
            _t(lang, "scarify.soon_cold_next"),
            _t(lang, "scarify.soon_cold", temp=f"{soil_temp:.0f}"),
            days_since,
            cooldown,
            reason_code="soon_soil_cold",
            next_window_code="when_soil_warm",
        )
    if growth < 50:
        return _result(
            ACTION_STATE_SOON, _t(lang, "scarify.soon_growth_next"), _t(lang, "scarify.soon_growth"),
            days_since, cooldown, reason_code="soon_growth", next_window_code="at_active_growth",
        )
    if rain_24h_mm >= 3 or rain_risk >= 50:
        return _result(
            ACTION_STATE_WAIT, _t(lang, "scarify.wait_wet_next"), _t(lang, "scarify.wait_wet"),
            days_since, cooldown, reason_code="wait_wet", next_window_code="after_dry_days",
        )
    return _result(
        ACTION_STATE_DO_NOW, _t(lang, "scarify.do_now_next"), _t(lang, "scarify.do_now"),
        days_since, cooldown, reason_code="do_now", next_window_code="today",
    )


def _action_aerate(
    moisture: float | None,
    soil_temp: float | None,
    phase: str,
    month: int,
    windows: dict[str, tuple[tuple[int, int], ...]],
    days_since: int | None,
    lang: str = DEFAULT_LANGUAGE,
) -> dict[str, Any]:
    cooldown = ACTION_COOLDOWN_DAYS[ACTION_AERATE]
    win = windows.get(ACTION_AERATE, ())
    if not _in_window(month, win):
        return _result(
            ACTION_STATE_OFF_SEASON, _next_window_label(month, win, lang), _t(lang, "aerate.off_season"),
            days_since, cooldown, reason_code="off_season", next_window_code="next_season_month",
        )
    if phase == "dormant":
        return _result(
            ACTION_STATE_SKIP, _t(lang, "aerate.skip_dormant_next"), _t(lang, "aerate.skip_dormant"),
            days_since, cooldown, reason_code="skip_dormant", next_window_code="after_growth_start",
        )
    if days_since is not None and days_since < cooldown:
        return _result(
            ACTION_STATE_WAIT,
            _t(lang, "aerate.wait_cooldown_next"),
            _t(lang, "aerate.wait_cooldown", days=days_since),
            days_since,
            cooldown,
            reason_code="wait_cooldown",
            next_window_code="next_season",
        )
    if soil_temp is not None and soil_temp < 8:
        return _result(
            ACTION_STATE_SOON,
            _t(lang, "aerate.soon_cold_next"),
            _t(lang, "aerate.soon_cold", temp=f"{soil_temp:.0f}"),
            days_since,
            cooldown,
            reason_code="soon_soil_cold",
            next_window_code="when_soil_warm",
        )
    if moisture is not None and moisture > 75:
        return _result(
            ACTION_STATE_WAIT, _t(lang, "aerate.wait_wet_next"), _t(lang, "aerate.wait_wet"),
            days_since, cooldown, reason_code="wait_wet", next_window_code="after_dry_out",
        )
    return _result(
        ACTION_STATE_DO_NOW, _t(lang, "aerate.do_now_next"), _t(lang, "aerate.do_now"),
        days_since, cooldown, reason_code="do_now", next_window_code="today",
    )


def _action_overseed(
    soil_temp: float | None,
    stress: float,
    month: int,
    windows: dict[str, tuple[tuple[int, int], ...]],
    daily: list[dict[str, Any]],
    days_since: int | None,
    lang: str = DEFAULT_LANGUAGE,
) -> dict[str, Any]:
    cooldown = ACTION_COOLDOWN_DAYS[ACTION_OVERSEED]
    win = windows.get(ACTION_OVERSEED, ())
    if not _in_window(month, win):
        return _result(
            ACTION_STATE_OFF_SEASON, _next_window_label(month, win, lang), _t(lang, "overseed.off_season"),
            days_since, cooldown, reason_code="off_season", next_window_code="next_season_month",
        )
    if stress >= 60:
        return _result(
            ACTION_STATE_SKIP, _t(lang, "overseed.skip_stress_next"), _t(lang, "overseed.skip_stress"),
            days_since, cooldown, reason_code="skip_stress", next_window_code="after_recovery",
        )
    if days_since is not None and days_since < cooldown:
        return _result(
            ACTION_STATE_WAIT,
            _t(lang, "overseed.wait_cooldown_next", days=cooldown - days_since),
            _t(lang, "overseed.wait_cooldown", days=days_since),
            days_since,
            cooldown,
            reason_code="wait_cooldown",
            next_window_code="wait_days",
        )
    if soil_temp is not None and soil_temp < 10:
        return _result(
            ACTION_STATE_SOON,
            _t(lang, "overseed.soon_cold_next"),
            _t(lang, "overseed.soon_cold", temp=f"{soil_temp:.0f}"),
            days_since,
            cooldown,
            reason_code="soon_soil_cold",
            next_window_code="when_soil_warm",
        )
    if _has_extreme_forecast(daily[:14]):
        return _result(
            ACTION_STATE_WAIT, _t(lang, "overseed.wait_extreme_next"), _t(lang, "overseed.wait_extreme"),
            days_since, cooldown, reason_code="wait_extreme_weather", next_window_code="after_weather_change",
        )
    return _result(
        ACTION_STATE_DO_NOW, _t(lang, "overseed.do_now_next"), _t(lang, "overseed.do_now"),
        days_since, cooldown, reason_code="do_now", next_window_code="this_week",
    )


def _has_extreme_forecast(daily: list[dict[str, Any]]) -> bool:
    for item in daily:
        high = _forecast_number(item, "temperature")
        low = _forecast_number(item, "templow")
        if high is not None and high >= 30:
            return True
        if low is not None and low <= 2:
            return True
    return False


def _next_dry_window(
    hourly: list[dict[str, Any]], lang: str = DEFAULT_LANGUAGE
) -> str | None:
    for item in hourly[:48]:
        probability = _forecast_number(item, "precipitation_probability", 0) or 0
        precipitation = _forecast_number(item, "precipitation", 0) or 0
        if probability <= 30 and precipitation <= 0.3:
            return _format_forecast_time(item.get("datetime"), lang)
    return None


def _in_window(month: int, windows: tuple[tuple[int, int], ...]) -> bool:
    return any(start <= month <= end for start, end in windows)


def _next_window_label(
    month: int,
    windows: tuple[tuple[int, int], ...],
    lang: str = DEFAULT_LANGUAGE,
) -> str:
    if not windows:
        return _t(lang, "next_window.dash")
    months = MONTH_NAMES.get(lang, MONTH_NAMES[DEFAULT_LANGUAGE])
    upcoming = [start for start, _ in windows if start > month]
    if upcoming:
        return months[min(upcoming) - 1]
    next_start = min(start for start, _ in windows)
    return _t(lang, "next_window.next_year", month=months[next_start - 1])


def _days_since_state(state_str: str | None, now: datetime) -> int | None:
    raw = str(state_str).strip() if state_str else ""
    if not raw:
        return None
    # Pure date strings (YYYY-MM-DD) should be compared as calendar days to
    # avoid timezone drift around midnight; only ISO datetimes carry a time.
    if "T" not in raw and " " not in raw:
        try:
            parsed_date = datetime.fromisoformat(raw).date()
        except ValueError:
            return None
        delta_days = (now.date() - parsed_date).days
        return max(0, delta_days)

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=now.tzinfo or timezone.utc)
    delta = now - parsed
    if delta.total_seconds() < 0:
        return 0
    return int(delta.total_seconds() // 86400)


def _result(
    state: str,
    next_window: str,
    reason: str,
    days_since: int | None,
    cooldown_days: int,
    *,
    reason_code: str | None = None,
    next_window_code: str | None = None,
) -> dict[str, Any]:
    return {
        "state": state,
        "next_window": next_window,
        "next_window_code": next_window_code,
        "reason": reason,
        "reason_code": reason_code,
        "days_since": days_since,
        "cooldown_days": cooldown_days,
    }


def _next_action(actions: dict[str, dict[str, Any]]) -> str:
    for target in (ACTION_STATE_DO_NOW, ACTION_STATE_SOON):
        for action in NEXT_ACTION_PRIORITY:
            if actions.get(action, {}).get("state") == target:
                return action
    return "none"


def _care_plan_7d(
    forecast: dict[str, list[dict[str, Any]]],
    inputs: LawnInputs,
    now: datetime,
    lang: str = DEFAULT_LANGUAGE,
) -> dict[str, Any]:
    """Build a per-day plan for the next 7 days from the daily forecast."""
    daily = forecast.get("daily") or []
    if not daily:
        return {"days": [], "actionable": 0, "rain_days": 0, "heat_days": 0}

    weekdays = WEEKDAY_NAMES.get(lang, WEEKDAY_NAMES[DEFAULT_LANGUAGE])
    plan: list[dict[str, Any]] = []
    for index, item in enumerate(daily[:7]):
        date_str = str(item.get("datetime", ""))[:10]
        try:
            parsed = datetime.fromisoformat(date_str)
            day_label = weekdays[parsed.weekday()]
        except (TypeError, ValueError):
            parsed = now + timedelta(days=index)
            date_str = parsed.date().isoformat()
            day_label = (
                _t(lang, "best_window.today") if index == 0
                else weekdays[parsed.weekday()]
            )

        temp_max = _forecast_number(item, "temperature")
        temp_min = _forecast_number(item, "templow")
        precip = _forecast_number(item, "precipitation", 0) or 0
        rain_prob = _forecast_number(item, "precipitation_probability", 0) or 0
        condition = str(item.get("condition", "")).lower()

        hint, icon, tone, hint_code = _care_plan_day_hint(
            temp_max, temp_min, precip, rain_prob, condition, inputs.grass_type, lang
        )

        plan.append({
            "date": date_str,
            "day": day_label,
            "temp_max": _round_or_none(temp_max, 0),
            "temp_min": _round_or_none(temp_min, 0),
            "precipitation_mm": round(precip, 1),
            "rain_probability": round(rain_prob),
            "hint": hint,
            "hint_code": hint_code,
            "icon": icon,
            "tone": tone,
        })

    actionable = sum(1 for d in plan if d["tone"] == "good")
    rain_days = sum(1 for d in plan if d["icon"] == "mdi:weather-pouring")
    heat_days = sum(1 for d in plan if d["icon"] == "mdi:weather-sunny-alert")
    return {
        "days": plan,
        "actionable": actionable,
        "rain_days": rain_days,
        "heat_days": heat_days,
    }


def _care_plan_day_hint(
    temp_max: float | None,
    temp_min: float | None,
    precip: float,
    rain_prob: float,
    condition: str,
    grass_type: str,
    lang: str = DEFAULT_LANGUAGE,
) -> tuple[str, str, str, str]:
    if temp_min is not None and temp_min <= 2:
        return (_t(lang, "plan.frost"), "mdi:snowflake", "muted", "frost")
    if temp_max is not None and temp_max >= 30:
        return (_t(lang, "plan.heat"), "mdi:weather-sunny-alert", "warn", "heat")
    if precip >= 5 or rain_prob >= 70 or condition in {"pouring", "rainy"}:
        return (_t(lang, "plan.rain"), "mdi:weather-pouring", "muted", "rain")
    if temp_max is None:
        return (_t(lang, "plan.unknown"), "mdi:weather-cloudy", "muted", "unknown")
    base = 10 if grass_type == GRASS_WARM_SEASON else 5
    if temp_max < base + 4:
        return (_t(lang, "plan.cool"), "mdi:weather-fog", "muted", "cool")
    if temp_max >= 18 and rain_prob < 40 and precip < 1:
        return (_t(lang, "plan.mowing"), "mdi:robot-mower", "good", "mowing")
    return (_t(lang, "plan.stable"), "mdi:weather-partly-cloudy", "neutral", "stable")
