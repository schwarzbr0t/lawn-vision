"""Data coordinator and lawn calculations for Lawn Vision."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from math import exp
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_AREA_M2,
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
    CONF_TEMPERATURE_ENTITY,
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
    SENSOR_PHASE,
    SENSOR_RECOMMENDATION,
    SENSOR_SOIL_TEMPERATURE,
    SENSOR_STRESS_LEVEL,
    SENSOR_WATER_NEED,
)

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

    @property
    def config(self) -> dict[str, Any]:
        """Return merged configuration and options."""
        return {**self.entry.data, **self.entry.options}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch states and calculate lawn metrics."""
        config = self.config
        weather_state = self._state(config.get(CONF_WEATHER_ENTITY))

        inputs = LawnInputs(
            temperature_c=self._number_from_entity(
                config.get(CONF_TEMPERATURE_ENTITY),
                weather_state.attributes.get("temperature") if weather_state else None,
            ),
            mean_daily_temperature_c=self._number_from_entity(
                config.get(CONF_MEAN_DAILY_TEMPERATURE_ENTITY)
            ),
            soil_temperature_c=self._number_from_entity(
                config.get(CONF_SOIL_TEMPERATURE_ENTITY)
            ),
            humidity_pct=self._number_from_entity(
                config.get(CONF_HUMIDITY_ENTITY),
                weather_state.attributes.get("humidity") if weather_state else None,
            ),
            moisture_pct=self._number_from_entity(config.get(CONF_MOISTURE_ENTITY)),
            moisture_10cm_m3m3=self._moisture_m3m3_from_entity(
                config.get(CONF_MOISTURE_10CM_ENTITY)
            ),
            moisture_20cm_m3m3=self._moisture_m3m3_from_entity(
                config.get(CONF_MOISTURE_20CM_ENTITY)
            ),
            moisture_30cm_m3m3=self._moisture_m3m3_from_entity(
                config.get(CONF_MOISTURE_30CM_ENTITY)
            ),
            rain_mm=self._number_from_entity(
                config.get(CONF_RAIN_ENTITY),
                weather_state.attributes.get("precipitation") if weather_state else None,
            ),
            grassland_temperature_sum=self._number_from_entity(config.get(CONF_GTS_ENTITY)),
            growing_degree_days=self._number_from_entity(config.get(CONF_GDD_ENTITY)),
            condition=weather_state.state if weather_state else None,
            grass_type=config.get(CONF_GRASS_TYPE, DEFAULT_GRASS_TYPE),
            area_m2=float(config.get(CONF_AREA_M2, DEFAULT_AREA_M2)),
        )

        forecast = await self._async_get_forecast(config.get(CONF_WEATHER_ENTITY))
        metrics = calculate_metrics(inputs, forecast)
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
        }
        metrics["name"] = config.get(CONF_NAME, DEFAULT_NAME)
        return metrics

    def _state(self, entity_id: str | None):
        """Return an entity state if configured."""
        if not entity_id:
            return None
        return self.hass.states.get(entity_id)

    def _number_from_entity(
        self, entity_id: str | None, fallback: Any | None = None
    ) -> float | None:
        """Read a numeric value from an entity state or fallback."""
        value = fallback
        state = self._state(entity_id)
        if state is not None:
            value = state.state
        try:
            if value in (None, "unknown", "unavailable"):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

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


def calculate_metrics(
    inputs: LawnInputs, forecast: dict[str, list[dict[str, Any]]] | None = None
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
    recommendation = _recommendation(phase, growth, mowing, water_need, stress)
    forecast_metrics = _forecast_metrics(
        forecast or {"hourly": [], "daily": []}, inputs, mowing, stress, water_need
    )
    growing_degree_days = inputs.growing_degree_days
    if growing_degree_days is None:
        growing_degree_days = _growing_degree_days(mean_daily_temp, inputs.grass_type)

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
        SENSOR_RECOMMENDATION: recommendation,
        **forecast_metrics,
    }


def _forecast_metrics(
    forecast: dict[str, list[dict[str, Any]]],
    inputs: LawnInputs,
    mowing: float,
    stress: float,
    water_need: float,
) -> dict[str, Any]:
    hourly = forecast.get("hourly") or []
    daily = forecast.get("daily") or []
    usable = hourly or daily

    if not usable:
        return {
            SENSOR_FORECAST_RAIN_RISK: None,
            SENSOR_FORECAST_WATER_NEED: None,
            SENSOR_FORECAST_GROWTH_TREND: "unknown",
            SENSOR_FORECAST_BEST_WINDOW: "Keine Prognose verfuegbar",
            SENSOR_FORECAST_CARE_HINT: "Keine Forecast-Daten der Wetter-Entity verfuegbar.",
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
    best_window = _best_mowing_window(hourly, daily, mowing, rain_risk, stress)
    care_hint = _forecast_care_hint(best_window, forecast_water, rain_risk, trend, stress)

    return {
        SENSOR_FORECAST_RAIN_RISK: round(rain_risk),
        SENSOR_FORECAST_WATER_NEED: round(forecast_water, 1),
        SENSOR_FORECAST_GROWTH_TREND: trend,
        SENSOR_FORECAST_BEST_WINDOW: best_window,
        SENSOR_FORECAST_CARE_HINT: care_hint,
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
) -> str:
    if stress >= 65:
        return "Rasen schonen"
    if mowing < 45:
        return "Noch warten"

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
                return _format_forecast_time(item.get("datetime"))

    if daily:
        for index, item in enumerate(daily[:4]):
            probability = _forecast_number(item, "precipitation_probability", 0) or 0
            precipitation = _forecast_number(item, "precipitation", 0) or 0
            if probability <= 45 and precipitation <= 2.0:
                return "Heute" if index == 0 else f"+{index}T"

    if rain_risk >= 65:
        return "Nach Regen pruefen"
    return "Naechstes trockenes Fenster"


def _forecast_care_hint(
    best_window: str, water_need: float, rain_risk: float, trend: str, stress: float
) -> str:
    if stress >= 65:
        return "Stress bleibt relevant. Erst erholen lassen, dann maehen oder duengen."
    if water_need >= 8 and rain_risk < 55:
        return "Bewaesserung in den naechsten 48h sinnvoll."
    if rain_risk >= 70:
        return "Regenrisiko hoch. Maehen und Duengen verschieben."
    if trend == "rising":
        return f"Wachstum nimmt zu. Bestes Pflegefenster: {best_window}."
    if trend == "falling":
        return f"Wachstum laesst nach. Pflegefenster eher kurz nutzen: {best_window}."
    return f"Stabile Bedingungen. Bestes Pflegefenster: {best_window}."


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


def _format_forecast_time(value: Any) -> str:
    if not value:
        return "Bald"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return "Bald"
    return parsed.strftime("%a %H:%M")


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
) -> str:
    if phase == "dormant":
        return "Rasen ruht. Pflege niedrig halten und Boden nicht unnoetig belasten."
    if stress >= 70:
        return "Stress hoch. Nicht duengen oder tief maehen; Bewaesserung und Erholung priorisieren."
    if water_need >= 8:
        return "Bewaesserung sinnvoll. Lieber tief und selten waessern als kurz und haeufig."
    if mowing >= 72 and growth >= 55:
        return "Gutes Maehfenster. Nicht mehr als ein Drittel der Halmlaenge entfernen."
    if phase == "active_growth":
        return "Aktives Wachstum. Regelmaessig maehen und Naehrstoffversorgung im Blick behalten."
    if phase == "waking_up":
        return "Wachstum startet. Leichte Pflege ist ok, intensive Massnahmen noch vorsichtig planen."
    return "Wachstum langsam. Beobachten, aber groessere Pflegefenster abwarten."


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)


def _round_or_none(value: float | None, digits: int) -> float | None:
    if value is None:
        return None
    return round(value, digits)
