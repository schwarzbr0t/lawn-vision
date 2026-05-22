"""Data coordinator and lawn calculations for Lawn Vision."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from math import exp
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

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
    CONF_AREA_M2,
    CONF_ESTIMATE_FROM_WEATHER,
    CONF_GDD_ENTITY,
    CONF_GRASS_TYPE,
    CONF_GTS_ENTITY,
    CONF_HUMIDITY_ENTITY,
    CONF_MEAN_DAILY_TEMPERATURE_ENTITY,
    CONF_MOISTURE_ENTITY,
    CONF_MOISTURE_10CM_ENTITY,
    CONF_MOISTURE_20CM_ENTITY,
    CONF_MOISTURE_30CM_ENTITY,
    CONF_RAIN_ENTITY,
    CONF_SOIL_TEMPERATURE_ENTITY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_TEMPERATURE_ENTITY,
    CONF_USE_OPEN_METEO,
    CONF_WEATHER_ENTITY,
    DEFAULT_AREA_M2,
    DEFAULT_GRASS_TYPE,
    DEFAULT_NAME,
    DOMAIN,
    GRASS_COOL_SEASON,
    GRASS_WARM_SEASON,
    SENSOR_FORECAST_BEST_WINDOW,
    SENSOR_FORECAST_CARE_HINT,
    SENSOR_FORECAST_GROWTH_TREND,
    SENSOR_FORECAST_RAIN_RISK,
    SENSOR_FORECAST_WATER_NEED,
    FORECAST_SLOTS,
    SENSOR_GROWTH_SCORE,
    SENSOR_GROWING_DEGREE_DAYS,
    SENSOR_GRASSLAND_TEMPERATURE_SUM,
    SENSOR_MEAN_DAILY_TEMPERATURE,
    SENSOR_MOWING_CONDITION,
    SENSOR_MOISTURE_10CM,
    SENSOR_MOISTURE_20CM,
    SENSOR_MOISTURE_30CM,
    SENSOR_CARE_PLAN_7D,
    SENSOR_NEXT_ACTION,
    SENSOR_PHASE,
    SENSOR_RECOMMENDATION,
    SENSOR_SOIL_TEMPERATURE,
    SENSOR_STRESS_LEVEL,
    SENSOR_WATER_NEED,
)
from .actions import (
    ACTION_COOLDOWN_DAYS,
    ANNUAL_ACTIONS,
    NEXT_ACTION_PRIORITY,
    SEASONAL_WINDOWS_COOL,
    SEASONAL_WINDOWS_WARM,
    _action_aerate,
    _action_fertilize,
    _action_mow,
    _action_overseed,
    _action_scarify,
    _action_water,
    _care_actions,
    _care_plan_7d,
    _care_plan_day_hint,
    _days_since_state,
    _has_extreme_forecast,
    _in_window,
    _next_action,
    _next_dry_window,
    _next_window_label,
    _resolve_conflicts,
    _result,
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
from .translations import (
    DEFAULT_LANGUAGE,
    MONTH_NAMES,
    STRINGS,
    SUPPORTED_LANGUAGES,
    WEEKDAY_NAMES,
    _resolve_language,
    _t,
)
from .weather_source import fetch_open_meteo

# Re-export for backward compatibility with code (and tests) that imported
# these names directly from `lawn_vision.coordinator`.
__all__ = [
    "DEFAULT_LANGUAGE",
    "MONTH_NAMES",
    "STRINGS",
    "SUPPORTED_LANGUAGES",
    "WEEKDAY_NAMES",
    "_resolve_language",
    "_t",
]

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class LawnInputs:
    """Normalized inputs for lawn calculations."""

    temperature_c: float | None
    mean_daily_temperature_c: float | None
    soil_temperature_c: float | None
    humidity_pct: float | None
    moisture_pct: float | None
    moisture_10cm_m3m3: float | None
    moisture_20cm_m3m3: float | None
    moisture_30cm_m3m3: float | None
    rain_mm: float | None
    grassland_temperature_sum: float | None
    growing_degree_days: float | None
    condition: str | None
    grass_type: str
    area_m2: float
    soil_temperature_estimated: bool = False
    moisture_estimated: bool = False


class LawnVisionCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate Lawn Vision data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=15),
        )
        self.entry = entry
        self.journal: dict[str, str | None] = {}
        self._soil_temp_estimate: float | None = None
        self._soil_moisture_estimate: float | None = None
        self._last_update: datetime | None = None

    @property
    def config(self) -> dict[str, Any]:
        """Return merged configuration and options."""
        return {**self.entry.data, **self.entry.options}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch states and calculate lawn metrics."""
        config = self.config
        weather_state = self._state(config.get(CONF_WEATHER_ENTITY))

        om_payload: dict[str, Any] | None = None
        if config.get(CONF_USE_OPEN_METEO):
            latitude = config.get(CONF_LATITUDE)
            longitude = config.get(CONF_LONGITUDE)
            if latitude is None:
                latitude = self.hass.config.latitude
            if longitude is None:
                longitude = self.hass.config.longitude
            om_payload = await fetch_open_meteo(self.hass, latitude, longitude)
        om_current = (om_payload or {}).get("current", {}) if om_payload else {}

        weather_temp = weather_state.attributes.get("temperature") if weather_state else None
        weather_humidity = weather_state.attributes.get("humidity") if weather_state else None
        weather_precip = weather_state.attributes.get("precipitation") if weather_state else None
        condition = (weather_state.state if weather_state else None) or om_current.get("condition")

        air_temp = self._number_from_entity(
            config.get(CONF_TEMPERATURE_ENTITY),
            weather_temp,
            om_current.get("temperature_c"),
        )
        mean_daily_temp = self._number_from_entity(
            config.get(CONF_MEAN_DAILY_TEMPERATURE_ENTITY)
        )
        humidity = self._number_from_entity(
            config.get(CONF_HUMIDITY_ENTITY),
            weather_humidity,
            om_current.get("humidity_pct"),
        )
        rain = self._number_from_entity(
            config.get(CONF_RAIN_ENTITY),
            weather_precip,
            om_current.get("rain_mm"),
        )

        soil_temp_raw = self._number_from_entity(
            config.get(CONF_SOIL_TEMPERATURE_ENTITY),
            om_current.get("soil_temperature_c"),
        )
        moisture_raw = self._number_from_entity(
            config.get(CONF_MOISTURE_ENTITY),
            om_current.get("moisture_pct"),
        )

        soil_temp_estimated = False
        moisture_estimated = False
        if config.get(CONF_ESTIMATE_FROM_WEATHER):
            now = dt_util.now()
            elapsed_h = self._hours_since_last_update(now)
            if soil_temp_raw is None and (air_temp is not None or mean_daily_temp is not None):
                self._soil_temp_estimate = estimate_soil_temperature(
                    previous=self._soil_temp_estimate,
                    air_temp_c=air_temp,
                    mean_daily_temp_c=mean_daily_temp,
                    elapsed_hours=elapsed_h,
                )
                if self._soil_temp_estimate is not None:
                    soil_temp_raw = self._soil_temp_estimate
                    soil_temp_estimated = True
            if moisture_raw is None and air_temp is not None:
                self._soil_moisture_estimate = estimate_soil_moisture(
                    previous=self._soil_moisture_estimate,
                    rain_mm=rain,
                    humidity_pct=humidity,
                    air_temp_c=air_temp,
                    elapsed_hours=elapsed_h,
                )
                if self._soil_moisture_estimate is not None:
                    moisture_raw = self._soil_moisture_estimate
                    moisture_estimated = True
            self._last_update = now

        inputs = LawnInputs(
            temperature_c=air_temp,
            mean_daily_temperature_c=mean_daily_temp,
            soil_temperature_c=soil_temp_raw,
            humidity_pct=humidity,
            moisture_pct=moisture_raw,
            moisture_10cm_m3m3=self._moisture_m3m3_from_entity(
                config.get(CONF_MOISTURE_10CM_ENTITY)
            ),
            moisture_20cm_m3m3=self._moisture_m3m3_from_entity(
                config.get(CONF_MOISTURE_20CM_ENTITY)
            ),
            moisture_30cm_m3m3=self._moisture_m3m3_from_entity(
                config.get(CONF_MOISTURE_30CM_ENTITY)
            ),
            rain_mm=rain,
            grassland_temperature_sum=self._number_from_entity(config.get(CONF_GTS_ENTITY)),
            growing_degree_days=self._number_from_entity(config.get(CONF_GDD_ENTITY)),
            condition=condition,
            grass_type=config.get(CONF_GRASS_TYPE, DEFAULT_GRASS_TYPE),
            area_m2=float(config.get(CONF_AREA_M2, DEFAULT_AREA_M2)),
            soil_temperature_estimated=soil_temp_estimated,
            moisture_estimated=moisture_estimated,
        )

        if om_payload and om_payload.get("forecast"):
            forecast = om_payload["forecast"]
            weather_source = "open_meteo"
        else:
            forecast = await self._async_get_forecast(config.get(CONF_WEATHER_ENTITY))
            weather_source = "weather_entity" if weather_state else "local"
        last_done: dict[str, str | None] = {}
        for action in CARE_ACTIONS:
            override = self._state_string(config.get(ACTION_LAST_DONE_KEYS[action]))
            last_done[action] = override if override else self.journal.get(action)
        lang = _resolve_language(getattr(self.hass.config, "language", None))
        metrics = calculate_metrics(inputs, forecast, last_done, dt_util.now(), lang=lang)
        metrics["inputs"] = {
            "temperature_c": inputs.temperature_c,
            "mean_daily_temperature_c": inputs.mean_daily_temperature_c,
            "soil_temperature_c": inputs.soil_temperature_c,
            "humidity_pct": inputs.humidity_pct,
            "moisture_pct": inputs.moisture_pct,
            "moisture_10cm_m3m3": inputs.moisture_10cm_m3m3,
            "moisture_20cm_m3m3": inputs.moisture_20cm_m3m3,
            "moisture_30cm_m3m3": inputs.moisture_30cm_m3m3,
            "rain_mm": inputs.rain_mm,
            "grassland_temperature_sum": inputs.grassland_temperature_sum,
            "growing_degree_days": inputs.growing_degree_days,
            "condition": inputs.condition,
            "grass_type": inputs.grass_type,
            "area_m2": inputs.area_m2,
            "weather_source": weather_source,
            "soil_temperature_estimated": inputs.soil_temperature_estimated,
            "moisture_estimated": inputs.moisture_estimated,
            "language": lang,
        }
        metrics["name"] = config.get(CONF_NAME, DEFAULT_NAME)
        return metrics

    def _state(self, entity_id: str | None):
        """Return an entity state if configured."""
        if not entity_id:
            return None
        return self.hass.states.get(entity_id)

    def _state_string(self, entity_id: str | None) -> str | None:
        """Return the raw state string of an entity, or None when unavailable."""
        state = self._state(entity_id)
        if state is None:
            return None
        if state.state in (None, "unknown", "unavailable", ""):
            return None
        return state.state

    def _number_from_entity(
        self, entity_id: str | None, *fallbacks: Any
    ) -> float | None:
        """Read a numeric value from an entity, or fall back to the first usable value."""
        state = self._state(entity_id)
        if state is not None and state.state not in (None, "unknown", "unavailable", ""):
            try:
                return float(state.state)
            except (TypeError, ValueError):
                pass
        for fb in fallbacks:
            if fb in (None, "unknown", "unavailable", ""):
                continue
            try:
                return float(fb)
            except (TypeError, ValueError):
                continue
        return None

    def _hours_since_last_update(self, now: datetime) -> float | None:
        """Return hours since the previous coordinator tick, or None on the first run."""
        prev = self._last_update
        if prev is None:
            return None
        delta = (now - prev).total_seconds() / 3600
        if delta <= 0:
            return None
        return min(delta, 24)

    def _moisture_m3m3_from_entity(self, entity_id: str | None) -> float | None:
        """Read volumetric soil moisture and normalize percent sensors to m3/m3."""
        value = self._number_from_entity(entity_id)
        if value is None:
            return None
        if value > 1.5:
            value = value / 100
        return round(_clamp(value, 0, 1), 3)

    async def _async_get_forecast(
        self, weather_entity_id: str | None
    ) -> dict[str, list[dict[str, Any]]]:
        """Return hourly and daily forecasts from a weather entity."""
        if not weather_entity_id:
            return {"hourly": [], "daily": []}

        return {
            "hourly": await self._async_get_forecast_type(weather_entity_id, "hourly"),
            "daily": await self._async_get_forecast_type(weather_entity_id, "daily"),
        }

    async def _async_get_forecast_type(
        self, weather_entity_id: str, forecast_type: str
    ) -> list[dict[str, Any]]:
        """Call Home Assistant's weather forecast response service."""
        try:
            response = await self.hass.services.async_call(
                "weather",
                "get_forecasts",
                {"entity_id": weather_entity_id, "type": forecast_type},
                blocking=True,
                return_response=True,
            )
        except (HomeAssistantError, TypeError, ValueError) as err:
            LOGGER.debug("Could not fetch %s forecast: %s", forecast_type, err)
            return []

        if not isinstance(response, dict):
            return []
        entity_response = response.get(weather_entity_id) or next(
            iter(response.values()), {}
        )
        forecast = entity_response.get("forecast") if isinstance(entity_response, dict) else None
        return forecast if isinstance(forecast, list) else []




def estimate_soil_temperature(
    *,
    previous: float | None,
    air_temp_c: float | None,
    mean_daily_temp_c: float | None,
    elapsed_hours: float | None,
) -> float | None:
    """Estimate soil temperature at ~10 cm from air temperature.

    Approximates the well-known lag between air and soil temperature using
    exponential smoothing. Reference value is the mean daily temperature when
    available, otherwise the instantaneous air temperature shifted slightly to
    account for soil thermal buffering. ``elapsed_hours`` lets the smoothing
    weight scale with the real coordinator interval; ``None`` falls back to a
    sensible default for the first tick.
    """
    reference = mean_daily_temp_c
    if reference is None:
        reference = air_temp_c
    if reference is None:
        return previous
    target = reference - 1.5 if reference > 5 else reference - 0.5
    if previous is None:
        return round(_clamp(target, -10, 45), 2)
    hours = 1.0 if elapsed_hours is None else max(elapsed_hours, 0.1)
    # half-life ~36h → exp(-h / 52) (52 ≈ 36 / ln 2)
    alpha = 1 - exp(-hours / 52)
    smoothed = previous + alpha * (target - previous)
    return round(_clamp(smoothed, -10, 45), 2)


def estimate_soil_moisture(
    *,
    previous: float | None,
    rain_mm: float | None,
    humidity_pct: float | None,
    air_temp_c: float | None,
    elapsed_hours: float | None,
) -> float | None:
    """Estimate soil moisture (%) with a tiny daily water balance.

    Adds rain as inflow (1 mm ≈ 1.5 %-point assuming a shallow, sandy-loam-ish
    rooting zone), subtracts evapotranspiration driven by temperature and
    inverse humidity, and clamps to a realistic band. Persisted previous value
    is required for the running balance; the first tick seeds from a neutral
    35 %.
    """
    start = previous if previous is not None else 35.0
    hours = 1.0 if elapsed_hours is None else max(elapsed_hours, 0.1)
    fraction_of_day = min(hours / 24, 1.0)

    rain_gain = min((rain_mm or 0) * 1.5, 25) if rain_mm and rain_mm > 0 else 0
    et_pressure = max((air_temp_c or 0) - 10, 0) * 0.35
    humidity_brake = max(70 - (humidity_pct if humidity_pct is not None else 60), 0) * 0.04
    et_loss = (et_pressure + humidity_brake) * fraction_of_day

    value = start + rain_gain - et_loss
    return round(_clamp(value, 5, 85), 1)


def calculate_metrics(
    inputs: LawnInputs,
    forecast: dict[str, list[dict[str, Any]]] | None = None,
    last_done: dict[str, str | None] | None = None,
    now: datetime | None = None,
    lang: str = DEFAULT_LANGUAGE,
) -> dict[str, Any]:
    """Calculate lawn health and care recommendations."""
    temp = inputs.temperature_c
    mean_daily_temp = inputs.mean_daily_temperature_c or temp
    soil_temp = inputs.soil_temperature_c
    humidity = inputs.humidity_pct
    moisture = inputs.moisture_pct
    if moisture is None and inputs.moisture_10cm_m3m3 is not None:
        moisture = inputs.moisture_10cm_m3m3 * 100
    rain = inputs.rain_mm
    condition = (inputs.condition or "").lower()

    growth_temp = soil_temp if soil_temp is not None else temp
    growth = _growth_score(growth_temp, inputs.grass_type)
    moisture_factor = _moisture_factor(moisture, rain, humidity)
    heat_stress = _heat_stress(temp, moisture)
    drought_stress = _drought_stress(moisture, rain, humidity)
    wet_penalty = _wet_penalty(rain, condition, humidity)

    stress = round(_clamp(max(heat_stress, drought_stress, wet_penalty * 0.8), 0, 100))
    mowing = round(_clamp((growth * 0.55) + (moisture_factor * 0.35) - wet_penalty, 0, 100))
    water_need = _water_need_mm(temp, moisture, rain, humidity)
    phase = _phase(growth, stress, growth_temp, moisture)
    recommendation_code, recommendation_text = _recommendation(
        phase, growth, mowing, water_need, stress, lang
    )
    forecast_payload = forecast or {"hourly": [], "daily": []}
    forecast_metrics = _forecast_metrics(
        forecast_payload, inputs, mowing, stress, water_need, lang
    )
    growing_degree_days = inputs.growing_degree_days
    if growing_degree_days is None:
        growing_degree_days = _growing_degree_days(mean_daily_temp, inputs.grass_type)

    actions = _care_actions(
        inputs=inputs,
        forecast=forecast_payload,
        last_done=last_done or {},
        now=now or dt_util.now(),
        growth=growth,
        mowing=mowing,
        stress=stress,
        phase=phase,
        water_need=water_need,
        moisture=moisture,
        soil_temp=growth_temp,
        rain_risk_24h=forecast_metrics.get(SENSOR_FORECAST_RAIN_RISK) or 0,
        lang=lang,
    )
    next_action = _next_action(actions)
    care_plan_7d = _care_plan_7d(forecast_payload, inputs, now or dt_util.now(), lang)
    slots = _forecast_slots(
        forecast_payload.get("hourly") or [],
        forecast_payload.get("daily") or [],
        inputs,
        base_stress=stress,
        base_growth=growth_temp if growth_temp is not None else (mean_daily_temp or 0),
        lang=lang,
    )
    reasons = _recommendation_reasons(
        phase,
        growth,
        mowing,
        water_need,
        stress,
        forecast_metrics.get(SENSOR_FORECAST_RAIN_RISK) or 0,
        moisture,
        lang,
    )

    return {
        SENSOR_PHASE: phase,
        SENSOR_GROWTH_SCORE: round(growth),
        SENSOR_SOIL_TEMPERATURE: _round_or_none(soil_temp, 1),
        SENSOR_MEAN_DAILY_TEMPERATURE: _round_or_none(mean_daily_temp, 1),
        SENSOR_GRASSLAND_TEMPERATURE_SUM: _round_or_none(
            inputs.grassland_temperature_sum, 1
        ),
        SENSOR_GROWING_DEGREE_DAYS: _round_or_none(growing_degree_days, 1),
        SENSOR_MOISTURE_10CM: inputs.moisture_10cm_m3m3,
        SENSOR_MOISTURE_20CM: inputs.moisture_20cm_m3m3,
        SENSOR_MOISTURE_30CM: inputs.moisture_30cm_m3m3,
        SENSOR_MOWING_CONDITION: mowing,
        SENSOR_WATER_NEED: round(water_need, 1),
        SENSOR_STRESS_LEVEL: stress,
        SENSOR_RECOMMENDATION: recommendation_text,
        "recommendation_code": recommendation_code,
        "recommendation_reasons": reasons,
        SENSOR_NEXT_ACTION: next_action,
        SENSOR_CARE_PLAN_7D: care_plan_7d,
        "actions": actions,
        **{ACTION_SENSOR_KEYS[action]: actions[action] for action in CARE_ACTIONS},
        **forecast_metrics,
        **slots,
    }


def _forecast_metrics(
    forecast: dict[str, list[dict[str, Any]]],
    inputs: LawnInputs,
    mowing: float,
    stress: float,
    water_need: float,
    lang: str = DEFAULT_LANGUAGE,
) -> dict[str, Any]:
    hourly = forecast.get("hourly") or []
    daily = forecast.get("daily") or []
    usable = hourly or daily

    if not usable:
        return {
            SENSOR_FORECAST_RAIN_RISK: None,
            SENSOR_FORECAST_WATER_NEED: None,
            SENSOR_FORECAST_GROWTH_TREND: "unknown",
            SENSOR_FORECAST_BEST_WINDOW: _t(lang, "best_window.no_forecast"),
            "forecast_best_window_code": "no_forecast",
            SENSOR_FORECAST_CARE_HINT: _t(lang, "care_hint.no_forecast"),
            "forecast_care_hint_code": "no_forecast",
        }

    next_24h = hourly[:24] if hourly else daily[:1]
    next_48h = hourly[:48] if hourly else daily[:2]
    rain_risk = _forecast_rain_risk(next_24h)
    rain_mm_48h = sum(_forecast_number(item, "precipitation", 0) or 0 for item in next_48h)
    avg_temp_24h = _average(
        _forecast_number(item, "temperature") for item in next_24h
    )
    forecast_water = _clamp(
        water_need + max((avg_temp_24h or inputs.temperature_c or 18) - 24, 0) * 0.25 - rain_mm_48h * 0.7,
        0,
        18,
    )
    trend = _forecast_growth_trend(hourly, daily, inputs.grass_type)
    best_code, best_text = _best_mowing_window(
        hourly, daily, mowing, rain_risk, stress, lang
    )
    care_code, care_text = _forecast_care_hint(
        best_text, forecast_water, rain_risk, trend, stress, lang
    )

    return {
        SENSOR_FORECAST_RAIN_RISK: round(rain_risk),
        SENSOR_FORECAST_WATER_NEED: round(forecast_water, 1),
        SENSOR_FORECAST_GROWTH_TREND: trend,
        SENSOR_FORECAST_BEST_WINDOW: best_text,
        "forecast_best_window_code": best_code,
        SENSOR_FORECAST_CARE_HINT: care_text,
        "forecast_care_hint_code": care_code,
    }



def _forecast_growth_trend(
    hourly: list[dict[str, Any]], daily: list[dict[str, Any]], grass_type: str
) -> str:
    if hourly and len(hourly) >= 36:
        day_one = _average(_forecast_number(item, "temperature") for item in hourly[:24])
        day_two = _average(_forecast_number(item, "temperature") for item in hourly[24:48])
    elif len(daily) >= 2:
        day_one = _forecast_day_temperature(daily[0])
        day_two = _forecast_day_temperature(daily[1])
    else:
        return "unknown"

    if day_one is None or day_two is None:
        return "unknown"

    base = 10 if grass_type == GRASS_WARM_SEASON else 5
    diff = max(day_two - base, 0) - max(day_one - base, 0)
    if diff > 1.5:
        return "rising"
    if diff < -1.5:
        return "falling"
    return "stable"


def _best_mowing_window(
    hourly: list[dict[str, Any]],
    daily: list[dict[str, Any]],
    mowing: float,
    rain_risk: float,
    stress: float,
    lang: str = DEFAULT_LANGUAGE,
) -> tuple[str, str]:
    if stress >= 65:
        return "protect_lawn", _t(lang, "best_window.protect_lawn")
    if mowing < 45:
        return "wait_growth", _t(lang, "best_window.wait_growth")

    if hourly:
        for item in hourly[:72]:
            probability = _forecast_number(item, "precipitation_probability", 0) or 0
            precipitation = _forecast_number(item, "precipitation", 0) or 0
            temperature = _forecast_number(item, "temperature", 18) or 18
            condition = str(item.get("condition", "")).lower()
            if (
                probability <= 35
                and precipitation <= 0.3
                and 7 <= temperature <= 29
                and condition not in {"rainy", "pouring", "lightning", "hail", "snowy"}
            ):
                return "hourly_window", _format_forecast_time(item.get("datetime"), lang)

    if daily:
        for index, item in enumerate(daily[:4]):
            probability = _forecast_number(item, "precipitation_probability", 0) or 0
            precipitation = _forecast_number(item, "precipitation", 0) or 0
            if probability <= 45 and precipitation <= 2.0:
                if index == 0:
                    return "today", _t(lang, "best_window.today")
                return "plus_days", _t(lang, "best_window.plus_days", days=index)

    if rain_risk >= 65:
        return "after_rain", _t(lang, "best_window.after_rain")
    return "next_dry_window", _t(lang, "best_window.next_dry")


def _forecast_care_hint(
    best_window: str,
    water_need: float,
    rain_risk: float,
    trend: str,
    stress: float,
    lang: str = DEFAULT_LANGUAGE,
) -> tuple[str, str]:
    if stress >= 65:
        return "stress_recovery", _t(lang, "care_hint.stress")
    if water_need >= 8 and rain_risk < 55:
        return "water_within_48h", _t(lang, "care_hint.water_48h")
    if rain_risk >= 70:
        return "rain_risk_high", _t(lang, "care_hint.rain_risk")
    if trend == "rising":
        return "growth_rising", _t(lang, "care_hint.rising", window=best_window)
    if trend == "falling":
        return "growth_falling", _t(lang, "care_hint.falling", window=best_window)
    return "stable", _t(lang, "care_hint.stable", window=best_window)






def _growth_score(temp: float | None, grass_type: str) -> float:
    if temp is None:
        return 0

    optimum = 21 if grass_type == GRASS_COOL_SEASON else 29
    width = 7 if grass_type == GRASS_COOL_SEASON else 8
    score = 100 * exp(-((temp - optimum) ** 2) / (2 * width**2))

    if grass_type == GRASS_COOL_SEASON and temp > 30:
        score *= 0.55
    if grass_type != GRASS_COOL_SEASON and temp < 16:
        score *= 0.55
    if temp < 4:
        score = 0

    return _clamp(score, 0, 100)


def _growing_degree_days(mean_daily_temp: float | None, grass_type: str) -> float | None:
    if mean_daily_temp is None:
        return None
    base_temp = 10 if grass_type == GRASS_WARM_SEASON else 5
    return max(mean_daily_temp - base_temp, 0)


def _moisture_factor(
    moisture: float | None, rain: float | None, humidity: float | None
) -> float:
    if moisture is not None:
        return _clamp(100 - abs(moisture - 45) * 2.1, 0, 100)
    if rain is not None:
        return _clamp(82 - max(rain - 4, 0) * 8, 0, 100)
    if humidity is not None:
        return _clamp(45 + humidity * 0.45, 0, 90)
    return 62


def _heat_stress(temp: float | None, moisture: float | None) -> float:
    if temp is None:
        return 0
    base = max(temp - 28, 0) * 9
    if moisture is not None and moisture < 28:
        base += (28 - moisture) * 2.5
    return _clamp(base, 0, 100)


def _drought_stress(
    moisture: float | None, rain: float | None, humidity: float | None
) -> float:
    if moisture is not None:
        return _clamp((32 - moisture) * 4, 0, 100)
    if rain is not None and rain <= 0.2 and humidity is not None and humidity < 45:
        return 42
    return 0


def _wet_penalty(
    rain: float | None, condition: str, humidity: float | None
) -> float:
    penalty = 0
    if rain is not None:
        penalty += max(rain - 0.5, 0) * 13
    if condition in {"rainy", "pouring", "lightning", "hail", "snowy"}:
        penalty += 45
    if humidity is not None and humidity > 88:
        penalty += (humidity - 88) * 2
    return _clamp(penalty, 0, 100)


def _water_need_mm(
    temp: float | None,
    moisture: float | None,
    rain: float | None,
    humidity: float | None,
) -> float:
    if moisture is not None:
        deficit = max(38 - moisture, 0) * 0.75
    else:
        temp_pressure = max((temp or 18) - 22, 0) * 0.45
        humidity_pressure = max(55 - (humidity or 55), 0) * 0.08
        deficit = temp_pressure + humidity_pressure

    if rain is not None:
        deficit -= min(rain, 12) * 0.75

    return _clamp(deficit, 0, 18)


def _phase(
    growth: float, stress: float, temp: float | None, moisture: float | None
) -> str:
    if temp is not None and temp < 6:
        return "dormant"
    if stress >= 65:
        return "stress"
    if moisture is not None and moisture < 24:
        return "dry"
    if growth >= 72:
        return "active_growth"
    if growth >= 35:
        return "waking_up"
    return "slow_growth"


def _recommendation(
    phase: str,
    growth: float,
    mowing: float,
    water_need: float,
    stress: float,
    lang: str = DEFAULT_LANGUAGE,
) -> tuple[str, str]:
    if phase == "dormant":
        return "dormant_rest", _t(lang, "recommendation.dormant")
    if stress >= 70:
        return "stress_high", _t(lang, "recommendation.stress")
    if water_need >= 8:
        return "water_needed", _t(lang, "recommendation.water")
    if mowing >= 72 and growth >= 55:
        return "mowing_window", _t(lang, "recommendation.mow_window")
    if phase == "active_growth":
        return "active_growth", _t(lang, "recommendation.active_growth")
    if phase == "waking_up":
        return "waking_up", _t(lang, "recommendation.waking_up")
    return "slow_growth", _t(lang, "recommendation.slow")


def _forecast_slots(
    hourly: list[dict[str, Any]],
    daily: list[dict[str, Any]],
    inputs: LawnInputs,
    base_stress: float,
    base_growth: float,
    lang: str = DEFAULT_LANGUAGE,
) -> dict[str, dict[str, Any]]:
    """Build forecast slots (+24h / +48h / +3d) used by the dashboard card."""
    out: dict[str, dict[str, Any]] = {}
    base = 10 if inputs.grass_type == GRASS_WARM_SEASON else 5
    base_growth_above = max((base_growth or 0) - base, 0)

    for sensor_key, hours in FORECAST_SLOTS:
        window_hourly: list[dict[str, Any]] = []
        if hourly:
            start = max(hours - 12, 0)
            window_hourly = hourly[start:hours] or hourly[:hours]
        elif daily:
            window_hourly = daily[: max(hours // 24, 1)]

        rain_pct = round(_forecast_rain_risk(window_hourly)) if window_hourly else 0
        rain_mm = sum(_forecast_number(item, "precipitation", 0) or 0 for item in window_hourly)
        avg_temp = _average(_forecast_number(item, "temperature") for item in window_hourly)

        diff = max((avg_temp or 0) - base, 0) - base_growth_above if avg_temp is not None else 0
        if diff > 2.0:
            growth_code = "rising"
        elif diff > 0.5:
            growth_code = "slight"
        elif diff < -2.0:
            growth_code = "falling"
        elif avg_temp is None:
            growth_code = "unknown"
        else:
            growth_code = "stable"

        heat = _heat_stress(avg_temp, inputs.moisture_pct)
        drought = 0.0
        if rain_mm < 1 and (inputs.moisture_pct or 100) < 35:
            drought = 30 + max(0, (avg_temp or 0) - 22) * 2
        wet = 35 if rain_mm > 12 else 0
        slot_stress = round(_clamp(max(heat, drought, wet, base_stress * 0.7), 0, 100))
        if slot_stress >= 60:
            stress_code = "high"
        elif slot_stress >= 30:
            stress_code = "mid"
        else:
            stress_code = "low"

        rain_penalty = min(rain_pct, 100) * 0.55 + min(rain_mm * 4, 30)
        growth_bonus = {"rising": 18, "slight": 10, "stable": 4, "falling": -10, "unknown": 0}[growth_code]
        stress_penalty = slot_stress * 0.55
        suitability = round(_clamp(72 + growth_bonus - rain_penalty - stress_penalty, 0, 100))

        if rain_pct >= 55 or rain_mm >= 6:
            action_code = "wait_rain"
        elif slot_stress >= 55:
            action_code = "stress_recovery"
        elif suitability >= 70 and growth_code in {"rising", "slight", "stable"}:
            action_code = "mow_possible"
        elif growth_code == "rising":
            action_code = "observe"
        else:
            action_code = "wait"

        out[sensor_key] = {
            "hours": hours,
            "rain_pct": rain_pct,
            "rain_mm": round(rain_mm, 1),
            "temp_c": _round_or_none(avg_temp, 1),
            "growth_code": growth_code,
            "growth_label": _t(lang, f"slot.growth.{growth_code}"),
            "stress_code": stress_code,
            "stress_label": _t(lang, f"slot.stress.{stress_code}"),
            "suitability": suitability,
            "action_code": action_code,
            "action_label": _t(lang, f"slot.action.{action_code}"),
        }

    return out


def _recommendation_reasons(
    phase: str,
    growth: float,
    mowing: float,
    water_need: float,
    stress: float,
    rain_risk: float,
    moisture_pct: float | None,
    lang: str = DEFAULT_LANGUAGE,
) -> list[dict[str, str]]:
    """Build the bullet list of why the recommendation was chosen."""
    reasons: list[tuple[str, bool]] = []
    if growth < 60:
        reasons.append(("growth_moderate", True))
    else:
        reasons.append(("growth_active", True))
    if rain_risk >= 50:
        reasons.append(("rain_rising", True))
    elif water_need >= 6:
        reasons.append(("water_needed", True))
    else:
        reasons.append(("dry_ahead", True))
    if stress < 40:
        reasons.append(("stress_low", True))
    elif stress < 70:
        reasons.append(("stress_mid", True))
    else:
        reasons.append(("stress_high", True))
    if moisture_pct is None:
        reasons.append(("moisture_unknown", True))
    elif moisture_pct >= 40:
        reasons.append(("moisture_ok", True))
    else:
        reasons.append(("moisture_low", True))

    return [
        {"code": code, "label": _t(lang, f"reason.{code}"), "ok": ok}
        for code, ok in reasons
    ]



