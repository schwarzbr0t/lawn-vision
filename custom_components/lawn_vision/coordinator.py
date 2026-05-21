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
from .weather_source import fetch_open_meteo

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


SUPPORTED_LANGUAGES: tuple[str, ...] = ("de", "en")
DEFAULT_LANGUAGE = "de"


def _resolve_language(raw: str | None) -> str:
    """Return one of the supported language codes from a raw HA language string."""
    if not raw:
        return DEFAULT_LANGUAGE
    short = str(raw).split("-", 1)[0].lower()
    return short if short in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


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
        SENSOR_NEXT_ACTION: next_action,
        SENSOR_CARE_PLAN_7D: care_plan_7d,
        "actions": actions,
        **{ACTION_SENSOR_KEYS[action]: actions[action] for action in CARE_ACTIONS},
        **forecast_metrics,
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


def _forecast_day_temperature(item: dict[str, Any]) -> float | None:
    high = _forecast_number(item, "temperature")
    low = _forecast_number(item, "templow")
    if high is not None and low is not None:
        return (high + low) / 2
    return high


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


def _average(values) -> float | None:
    numbers = [value for value in values if value is not None]
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


def _format_forecast_time(value: Any, lang: str = DEFAULT_LANGUAGE) -> str:
    if not value:
        return _t(lang, "soon")
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return _t(lang, "soon")
    weekday = WEEKDAY_NAMES.get(lang, WEEKDAY_NAMES[DEFAULT_LANGUAGE])[parsed.weekday()]
    return f"{weekday} {parsed.strftime('%H:%M')}"


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


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)


def _round_or_none(value: float | None, digits: int) -> float | None:
    if value is None:
        return None
    return round(value, digits)


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

MONTH_NAMES: dict[str, tuple[str, ...]] = {
    "de": (
        "Januar",
        "Februar",
        "Maerz",
        "April",
        "Mai",
        "Juni",
        "Juli",
        "August",
        "September",
        "Oktober",
        "November",
        "Dezember",
    ),
    "en": (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
}
MONTH_NAMES_DE: tuple[str, ...] = MONTH_NAMES["de"]


STRINGS: dict[str, dict[str, str]] = {
    "de": {
        "recommendation.dormant": "Rasen ruht. Pflege niedrig halten und Boden nicht unnoetig belasten.",
        "recommendation.stress": "Stress hoch. Nicht duengen oder tief maehen; Bewaesserung und Erholung priorisieren.",
        "recommendation.water": "Bewaesserung sinnvoll. Lieber tief und selten waessern als kurz und haeufig.",
        "recommendation.mow_window": "Gutes Maehfenster. Nicht mehr als ein Drittel der Halmlaenge entfernen.",
        "recommendation.active_growth": "Aktives Wachstum. Regelmaessig maehen und Naehrstoffversorgung im Blick behalten.",
        "recommendation.waking_up": "Wachstum startet. Leichte Pflege ist ok, intensive Massnahmen noch vorsichtig planen.",
        "recommendation.slow": "Wachstum langsam. Beobachten, aber groessere Pflegefenster abwarten.",

        "best_window.protect_lawn": "Rasen schonen",
        "best_window.wait_growth": "Noch warten",
        "best_window.after_rain": "Nach Regen pruefen",
        "best_window.next_dry": "Naechstes trockenes Fenster",
        "best_window.no_forecast": "Keine Prognose verfuegbar",
        "best_window.today": "Heute",
        "best_window.plus_days": "+{days}T",

        "care_hint.stress": "Stress bleibt relevant. Erst erholen lassen, dann maehen oder duengen.",
        "care_hint.water_48h": "Bewaesserung in den naechsten 48h sinnvoll.",
        "care_hint.rain_risk": "Regenrisiko hoch. Maehen und Duengen verschieben.",
        "care_hint.rising": "Wachstum nimmt zu. Bestes Pflegefenster: {window}.",
        "care_hint.falling": "Wachstum laesst nach. Pflegefenster eher kurz nutzen: {window}.",
        "care_hint.stable": "Stabile Bedingungen. Bestes Pflegefenster: {window}.",
        "care_hint.no_forecast": "Keine Forecast-Daten der Wetter-Entity verfuegbar.",

        "soon": "Bald",
        "next_window.next_year": "{month} (naechstes Jahr)",
        "next_window.dash": "—",

        "mow.skip_dormant": "Rasen ruht – nicht maehen.",
        "mow.skip_stress": "Stress hoch – Maehen verschieben.",
        "mow.skip_stress_next": "Nach Erholung",
        "mow.wait_recent": "Vor {days} Tag(en) gemaeht – Rasen regenerieren lassen.",
        "mow.wait_recent_next": "In {days} T",
        "mow.do_now": "Wachstum aktiv und trockene Bedingungen.",
        "mow.do_now_next": "Heute",
        "mow.soon": "Bedingungen brauchbar – naechstes trockenes Fenster nutzen.",
        "mow.wait_rain": "Regen erwartet – nasser Schnitt schadet.",
        "mow.wait_rain_next": "Nach Regen",
        "mow.wait_growth": "Wachstum niedrig – Maehen lohnt noch nicht.",
        "mow.wait_growth_next": "Beobachten",

        "water.skip_dormant": "Rasen ruht – kein zusaetzliches Wasser noetig.",
        "water.wait_recent": "Vor Kurzem bewaessert – Boden ziehen lassen.",
        "water.wait_recent_next": "Morgen",
        "water.wait_rain": "Regen in 48h ~{mm} mm – Bewaesserung verschieben.",
        "water.wait_rain_next": "Nach Regen pruefen",
        "water.do_now": "Deutliches Defizit – tief und selten waessern.",
        "water.do_now_next": "Heute Abend",
        "water.soon": "Boden trocknet leicht – Bedarf beobachten.",
        "water.soon_next": "1–2 T",
        "water.ok": "Wasserhaushalt aktuell ok.",
        "water.ok_next": "Beobachten",

        "fert.off_season": "Ausserhalb der Duengesaison.",
        "fert.skip_dormant": "Rasen ruht – Duengen wirkt nicht.",
        "fert.skip_dormant_next": "Nach Wachstumsstart",
        "fert.skip_stress": "Stress hoch – erst Rasen stabilisieren.",
        "fert.skip_stress_next": "Nach Erholung",
        "fert.wait_cooldown": "Letzte Duengung vor {days} T – mind. 6 Wochen warten.",
        "fert.wait_cooldown_next": "In {days} T",
        "fert.soon_unknown": "Bodentemperatur unbekannt – Sensor ergaenzen fuer genauere Empfehlung.",
        "fert.soon_unknown_next": "Bei stabiler Bodenwaerme",
        "fert.wait_cold": "Boden noch zu kuehl ({temp} °C).",
        "fert.wait_cold_next": "Bei >8 °C Boden",
        "fert.soon_warm": "Boden fast warm genug ({temp} °C).",
        "fert.soon_warm_next": "Wenige Tage",
        "fert.do_now_unknown": "Letzte Duengung unbekannt – Helfer setzen fuer genauere Intervalle.",
        "fert.do_now_known": "Letzte Duengung vor {days} T.",
        "fert.do_now": "Boden warm ({temp} °C), Wachstum aktiv. {hint}",
        "fert.do_now_next": "Heute oder morgen",
        "fert.wait_slow": "Wachstum noch langsam – kurz abwarten.",
        "fert.wait_slow_next": "Bei Wachstumsschub",

        "scarify.off_season": "Vertikutieren nur im Fruehjahr oder Spaetsommer.",
        "scarify.skip_stress": "Rasen aktuell zu belastet zum Vertikutieren.",
        "scarify.skip_stress_next": "Nach Erholung",
        "scarify.wait_cooldown": "Vor {days} T vertikutiert – einmal pro Saison reicht.",
        "scarify.wait_cooldown_next": "Naechste Saison",
        "scarify.soon_cold": "Boden noch zu kuehl ({temp} °C).",
        "scarify.soon_cold_next": "Bei >10 °C Boden",
        "scarify.soon_growth": "Wachstum sollte aktiv sein, damit Rasen die Belastung wegsteckt.",
        "scarify.soon_growth_next": "Bei aktivem Wachstum",
        "scarify.wait_wet": "Boden zu nass – Vertikutieren reisst die Narbe auf.",
        "scarify.wait_wet_next": "Nach 2 trockenen Tagen",
        "scarify.do_now": "Boden trocken und warm, Wachstum aktiv.",
        "scarify.do_now_next": "Heute",

        "aerate.off_season": "Aerifizieren passt im Fruehjahr oder Herbst.",
        "aerate.skip_dormant": "Rasen ruht – Aerifizieren spaeter ansetzen.",
        "aerate.skip_dormant_next": "Nach Wachstumsstart",
        "aerate.wait_cooldown": "Vor {days} T aerifiziert – einmal pro Jahr ist ueblich.",
        "aerate.wait_cooldown_next": "Naechste Saison",
        "aerate.soon_cold": "Boden noch zu kuehl ({temp} °C).",
        "aerate.soon_cold_next": "Bei >8 °C Boden",
        "aerate.wait_wet": "Boden zu nass – Loecher wuerden verschmieren.",
        "aerate.wait_wet_next": "Nach Abtrocknen",
        "aerate.do_now": "Bedingungen passen – verdichtete Stellen entlueften.",
        "aerate.do_now_next": "Heute",

        "overseed.off_season": "Nachsaat wirkt nur in Saatfenstern.",
        "overseed.skip_stress": "Stress hoch – Keimlinge wuerden leiden.",
        "overseed.skip_stress_next": "Nach Erholung",
        "overseed.wait_cooldown": "Letzte Nachsaat vor {days} T – Keimung abwarten.",
        "overseed.wait_cooldown_next": "In {days} T",
        "overseed.soon_cold": "Boden noch zu kuehl ({temp} °C) fuer sichere Keimung.",
        "overseed.soon_cold_next": "Bei >10 °C Boden",
        "overseed.wait_extreme": "Hitze oder Frost in den naechsten 14 Tagen – Keimung gefaehrdet.",
        "overseed.wait_extreme_next": "Nach Wetterumschwung",
        "overseed.do_now": "Boden warm, stabiles Wetter – ideale Keimbedingungen.",
        "overseed.do_now_next": "Diese Woche",

        "conflict.annual_track": " Tipp: input_datetime-Helfer setzen, um Intervalle sauber zu rechnen.",
        "conflict.fert_after_scarify_reason": "Erst vertikutieren, dann nach 2–3 Tagen Regeneration duengen.",
        "conflict.fert_after_scarify_next": "2–3 Tage nach Vertikutieren",
        "conflict.aerate_skip_scarify_reason": "Vertikutieren und Aerifizieren nicht in derselben Pflegerunde kombinieren.",
        "conflict.aerate_skip_scarify_next": "Andere Pflegerunde",
        "conflict.overseed_starter_hint": " Tipp: Bei Nachsaat Starterduenger mit wenig Stickstoff einsetzen.",

        "plan.frost": "Frost erwartet",
        "plan.heat": "Hitze – bewaessern",
        "plan.rain": "Regen erwartet",
        "plan.unknown": "Wetter unbekannt",
        "plan.cool": "Boden noch kuehl",
        "plan.mowing": "Maehfenster",
        "plan.stable": "Stabil",
    },
    "en": {
        "recommendation.dormant": "Lawn is dormant. Keep care minimal and avoid stressing the soil.",
        "recommendation.stress": "Stress is high. Skip fertilizing and deep mowing; prioritize watering and recovery.",
        "recommendation.water": "Watering is sensible. Water deep and infrequently rather than little and often.",
        "recommendation.mow_window": "Good mowing window. Remove no more than a third of the blade length.",
        "recommendation.active_growth": "Active growth. Mow regularly and keep an eye on nutrient supply.",
        "recommendation.waking_up": "Growth is starting. Light care is fine, plan intensive measures carefully.",
        "recommendation.slow": "Growth is slow. Observe, but wait for larger care windows.",

        "best_window.protect_lawn": "Protect the lawn",
        "best_window.wait_growth": "Wait for growth",
        "best_window.after_rain": "Check after rain",
        "best_window.next_dry": "Next dry window",
        "best_window.no_forecast": "No forecast available",
        "best_window.today": "Today",
        "best_window.plus_days": "+{days}d",

        "care_hint.stress": "Stress is still relevant. Let the lawn recover first, then mow or fertilize.",
        "care_hint.water_48h": "Watering in the next 48 h makes sense.",
        "care_hint.rain_risk": "Rain risk is high. Postpone mowing and fertilizing.",
        "care_hint.rising": "Growth is rising. Best care window: {window}.",
        "care_hint.falling": "Growth is falling. Use the care window soon: {window}.",
        "care_hint.stable": "Stable conditions. Best care window: {window}.",
        "care_hint.no_forecast": "No forecast data available from the weather entity.",

        "soon": "Soon",
        "next_window.next_year": "{month} (next year)",
        "next_window.dash": "—",

        "mow.skip_dormant": "Lawn is dormant – don't mow.",
        "mow.skip_stress": "Stress high – postpone mowing.",
        "mow.skip_stress_next": "After recovery",
        "mow.wait_recent": "Mowed {days} day(s) ago – let the lawn regenerate.",
        "mow.wait_recent_next": "In {days} d",
        "mow.do_now": "Growth active and dry conditions.",
        "mow.do_now_next": "Today",
        "mow.soon": "Conditions workable – use the next dry window.",
        "mow.wait_rain": "Rain expected – a wet cut hurts the lawn.",
        "mow.wait_rain_next": "After rain",
        "mow.wait_growth": "Growth low – mowing isn't worthwhile yet.",
        "mow.wait_growth_next": "Observe",

        "water.skip_dormant": "Lawn is dormant – no extra water needed.",
        "water.wait_recent": "Recently watered – let the soil settle.",
        "water.wait_recent_next": "Tomorrow",
        "water.wait_rain": "Rain in 48 h ~{mm} mm – postpone watering.",
        "water.wait_rain_next": "Check after rain",
        "water.do_now": "Clear deficit – water deeply and infrequently.",
        "water.do_now_next": "This evening",
        "water.soon": "Soil drying slightly – monitor the need.",
        "water.soon_next": "1–2 d",
        "water.ok": "Water balance currently fine.",
        "water.ok_next": "Observe",

        "fert.off_season": "Outside fertilizing season.",
        "fert.skip_dormant": "Lawn is dormant – fertilizing won't work.",
        "fert.skip_dormant_next": "After growth starts",
        "fert.skip_stress": "Stress high – stabilize the lawn first.",
        "fert.skip_stress_next": "After recovery",
        "fert.wait_cooldown": "Last fertilized {days} d ago – wait at least 6 weeks.",
        "fert.wait_cooldown_next": "In {days} d",
        "fert.soon_unknown": "Soil temperature unknown – add a sensor for a more accurate hint.",
        "fert.soon_unknown_next": "When soil warms steadily",
        "fert.wait_cold": "Soil still too cold ({temp} °C).",
        "fert.wait_cold_next": "At >8 °C soil",
        "fert.soon_warm": "Soil almost warm enough ({temp} °C).",
        "fert.soon_warm_next": "A few days",
        "fert.do_now_unknown": "Last fertilizing unknown – set up the helper for precise intervals.",
        "fert.do_now_known": "Last fertilized {days} d ago.",
        "fert.do_now": "Soil warm ({temp} °C), growth active. {hint}",
        "fert.do_now_next": "Today or tomorrow",
        "fert.wait_slow": "Growth still slow – wait briefly.",
        "fert.wait_slow_next": "At a growth spurt",

        "scarify.off_season": "Scarify only in spring or late summer.",
        "scarify.skip_stress": "Lawn currently too stressed for scarifying.",
        "scarify.skip_stress_next": "After recovery",
        "scarify.wait_cooldown": "Scarified {days} d ago – once per season is enough.",
        "scarify.wait_cooldown_next": "Next season",
        "scarify.soon_cold": "Soil still too cold ({temp} °C).",
        "scarify.soon_cold_next": "At >10 °C soil",
        "scarify.soon_growth": "Growth should be active so the lawn can recover.",
        "scarify.soon_growth_next": "At active growth",
        "scarify.wait_wet": "Soil too wet – scarifying would tear the sward.",
        "scarify.wait_wet_next": "After 2 dry days",
        "scarify.do_now": "Soil dry and warm, growth active.",
        "scarify.do_now_next": "Today",

        "aerate.off_season": "Aerating works in spring or autumn.",
        "aerate.skip_dormant": "Lawn is dormant – schedule aerating later.",
        "aerate.skip_dormant_next": "After growth starts",
        "aerate.wait_cooldown": "Aerated {days} d ago – once per year is typical.",
        "aerate.wait_cooldown_next": "Next season",
        "aerate.soon_cold": "Soil still too cold ({temp} °C).",
        "aerate.soon_cold_next": "At >8 °C soil",
        "aerate.wait_wet": "Soil too wet – holes would smear.",
        "aerate.wait_wet_next": "After drying out",
        "aerate.do_now": "Conditions fit – vent compacted spots.",
        "aerate.do_now_next": "Today",

        "overseed.off_season": "Overseeding works only in seeding windows.",
        "overseed.skip_stress": "Stress high – seedlings would suffer.",
        "overseed.skip_stress_next": "After recovery",
        "overseed.wait_cooldown": "Last overseed {days} d ago – wait for germination.",
        "overseed.wait_cooldown_next": "In {days} d",
        "overseed.soon_cold": "Soil still too cold ({temp} °C) for reliable germination.",
        "overseed.soon_cold_next": "At >10 °C soil",
        "overseed.wait_extreme": "Heat or frost in the next 14 days – germination at risk.",
        "overseed.wait_extreme_next": "After weather change",
        "overseed.do_now": "Soil warm, stable weather – ideal germination conditions.",
        "overseed.do_now_next": "This week",

        "conflict.annual_track": " Tip: set an input_datetime helper to track intervals cleanly.",
        "conflict.fert_after_scarify_reason": "Scarify first, then fertilize after 2–3 days of recovery.",
        "conflict.fert_after_scarify_next": "2–3 days after scarifying",
        "conflict.aerate_skip_scarify_reason": "Don't combine scarifying and aerating in the same care round.",
        "conflict.aerate_skip_scarify_next": "Another care round",
        "conflict.overseed_starter_hint": " Tip: when overseeding, use a starter fertilizer low in nitrogen.",

        "plan.frost": "Frost expected",
        "plan.heat": "Heat – water",
        "plan.rain": "Rain expected",
        "plan.unknown": "Weather unknown",
        "plan.cool": "Soil still cool",
        "plan.mowing": "Mowing window",
        "plan.stable": "Stable",
    },
}


WEEKDAY_NAMES: dict[str, tuple[str, ...]] = {
    "de": ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"),
    "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
}


def _t(lang: str, key: str, **kwargs: Any) -> str:
    """Look up a localized string from STRINGS with safe English fallback."""
    table = STRINGS.get(lang) or STRINGS[DEFAULT_LANGUAGE]
    template = table.get(key) or STRINGS[DEFAULT_LANGUAGE].get(key, key)
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


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
    if not state_str:
        return None
    try:
        parsed = datetime.fromisoformat(str(state_str).replace("Z", "+00:00"))
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


WEEKDAY_NAMES_DE: tuple[str, ...] = WEEKDAY_NAMES["de"]


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
