"""Sensors for Lawn Vision."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ACTION_STATE_DO_NOW,
    ACTION_STATE_OFF_SEASON,
    ACTION_STATE_SKIP,
    ACTION_STATE_SOON,
    ACTION_STATE_WAIT,
    DOMAIN,
    SENSOR_ACTION_AERATE,
    SENSOR_ACTION_FERTILIZE,
    SENSOR_ACTION_MOW,
    SENSOR_ACTION_OVERSEED,
    SENSOR_ACTION_SCARIFY,
    SENSOR_ACTION_WATER,
    SENSOR_FORECAST_BEST_WINDOW,
    SENSOR_FORECAST_CARE_HINT,
    SENSOR_FORECAST_GROWTH_TREND,
    SENSOR_FORECAST_RAIN_RISK,
    SENSOR_FORECAST_SLOT_24H,
    SENSOR_FORECAST_SLOT_48H,
    SENSOR_FORECAST_SLOT_3D,
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
from .coordinator import LawnVisionCoordinator


@dataclass(frozen=True, kw_only=True)
class LawnVisionSensorDescription(SensorEntityDescription):
    """Description for a Lawn Vision sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    extra_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _action_state(key: str) -> Callable[[dict[str, Any]], Any]:
    def _value(data: dict[str, Any]) -> Any:
        info = data.get(key)
        return info.get("state") if isinstance(info, dict) else None

    return _value


def _action_extras(key: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def _value(data: dict[str, Any]) -> dict[str, Any]:
        info = data.get(key)
        if not isinstance(info, dict):
            return {}
        return {k: v for k, v in info.items() if k != "state"}

    return _value


ACTION_STATE_OPTIONS: list[str] = [
    ACTION_STATE_DO_NOW,
    ACTION_STATE_SOON,
    ACTION_STATE_WAIT,
    ACTION_STATE_SKIP,
    ACTION_STATE_OFF_SEASON,
]

NEXT_ACTION_OPTIONS: list[str] = [
    "mow",
    "water",
    "fertilize",
    "scarify",
    "aerate",
    "overseed",
    "none",
]


def _next_action_extras(data: dict[str, Any]) -> dict[str, Any]:
    action_id = data.get(SENSOR_NEXT_ACTION)
    if not action_id or action_id == "none":
        return {}
    info = data.get("actions", {}).get(action_id, {})
    return {
        "action": action_id,
        "next_window": info.get("next_window"),
        "next_window_code": info.get("next_window_code"),
        "reason": info.get("reason"),
        "reason_code": info.get("reason_code"),
        "days_since": info.get("days_since"),
        "cooldown_days": info.get("cooldown_days"),
    }


SENSORS: tuple[LawnVisionSensorDescription, ...] = (
    LawnVisionSensorDescription(
        key=SENSOR_PHASE,
        translation_key=SENSOR_PHASE,
        icon="mdi:grass",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "dormant",
            "stress",
            "dry",
            "active_growth",
            "waking_up",
            "slow_growth",
        ],
        value_fn=lambda data: data.get(SENSOR_PHASE),
        extra_fn=lambda data: data.get("inputs", {}),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_GROWTH_SCORE,
        translation_key=SENSOR_GROWTH_SCORE,
        icon="mdi:sprout",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(SENSOR_GROWTH_SCORE),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_SOIL_TEMPERATURE,
        translation_key=SENSOR_SOIL_TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        icon="mdi:thermometer-lines",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(SENSOR_SOIL_TEMPERATURE),
        extra_fn=lambda data: {
            "estimated": bool(data.get("inputs", {}).get("soil_temperature_estimated")),
        },
    ),
    LawnVisionSensorDescription(
        key=SENSOR_MEAN_DAILY_TEMPERATURE,
        translation_key=SENSOR_MEAN_DAILY_TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        icon="mdi:thermometer-auto",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(SENSOR_MEAN_DAILY_TEMPERATURE),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_GRASSLAND_TEMPERATURE_SUM,
        translation_key=SENSOR_GRASSLAND_TEMPERATURE_SUM,
        icon="mdi:sigma",
        native_unit_of_measurement="K",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(SENSOR_GRASSLAND_TEMPERATURE_SUM),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_GROWING_DEGREE_DAYS,
        translation_key=SENSOR_GROWING_DEGREE_DAYS,
        icon="mdi:chart-bell-curve-cumulative",
        native_unit_of_measurement="GDD",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(SENSOR_GROWING_DEGREE_DAYS),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_MOISTURE_10CM,
        translation_key=SENSOR_MOISTURE_10CM,
        icon="mdi:water-percent",
        native_unit_of_measurement="m3/m3",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(SENSOR_MOISTURE_10CM),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_MOISTURE_20CM,
        translation_key=SENSOR_MOISTURE_20CM,
        icon="mdi:water-percent",
        native_unit_of_measurement="m3/m3",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(SENSOR_MOISTURE_20CM),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_MOISTURE_30CM,
        translation_key=SENSOR_MOISTURE_30CM,
        icon="mdi:water-percent",
        native_unit_of_measurement="m3/m3",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(SENSOR_MOISTURE_30CM),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_MOWING_CONDITION,
        translation_key=SENSOR_MOWING_CONDITION,
        icon="mdi:content-cut",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(SENSOR_MOWING_CONDITION),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_WATER_NEED,
        translation_key=SENSOR_WATER_NEED,
        icon="mdi:water-percent",
        native_unit_of_measurement="mm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(SENSOR_WATER_NEED),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_STRESS_LEVEL,
        translation_key=SENSOR_STRESS_LEVEL,
        icon="mdi:alert-decagram-outline",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(SENSOR_STRESS_LEVEL),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_RECOMMENDATION,
        translation_key=SENSOR_RECOMMENDATION,
        icon="mdi:clipboard-text-outline",
        value_fn=lambda data: data.get(SENSOR_RECOMMENDATION),
        extra_fn=lambda data: {
            "code": data.get("recommendation_code"),
            "reasons": data.get("recommendation_reasons", []),
        },
    ),
    LawnVisionSensorDescription(
        key=SENSOR_FORECAST_RAIN_RISK,
        translation_key=SENSOR_FORECAST_RAIN_RISK,
        icon="mdi:weather-pouring",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(SENSOR_FORECAST_RAIN_RISK),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_FORECAST_WATER_NEED,
        translation_key=SENSOR_FORECAST_WATER_NEED,
        icon="mdi:watering-can-outline",
        native_unit_of_measurement="mm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(SENSOR_FORECAST_WATER_NEED),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_FORECAST_GROWTH_TREND,
        translation_key=SENSOR_FORECAST_GROWTH_TREND,
        icon="mdi:trending-up",
        device_class=SensorDeviceClass.ENUM,
        options=["rising", "falling", "stable", "unknown"],
        value_fn=lambda data: data.get(SENSOR_FORECAST_GROWTH_TREND),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_FORECAST_BEST_WINDOW,
        translation_key=SENSOR_FORECAST_BEST_WINDOW,
        icon="mdi:calendar-clock",
        value_fn=lambda data: data.get(SENSOR_FORECAST_BEST_WINDOW),
        extra_fn=lambda data: {"code": data.get("forecast_best_window_code")},
    ),
    LawnVisionSensorDescription(
        key=SENSOR_FORECAST_CARE_HINT,
        translation_key=SENSOR_FORECAST_CARE_HINT,
        icon="mdi:calendar-check-outline",
        value_fn=lambda data: data.get(SENSOR_FORECAST_CARE_HINT),
        extra_fn=lambda data: {"code": data.get("forecast_care_hint_code")},
    ),
    LawnVisionSensorDescription(
        key=SENSOR_FORECAST_SLOT_24H,
        translation_key=SENSOR_FORECAST_SLOT_24H,
        icon="mdi:clock-outline",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (data.get(SENSOR_FORECAST_SLOT_24H) or {}).get("suitability"),
        extra_fn=lambda data: {
            k: v for k, v in (data.get(SENSOR_FORECAST_SLOT_24H) or {}).items() if k != "suitability"
        },
    ),
    LawnVisionSensorDescription(
        key=SENSOR_FORECAST_SLOT_48H,
        translation_key=SENSOR_FORECAST_SLOT_48H,
        icon="mdi:clock-outline",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (data.get(SENSOR_FORECAST_SLOT_48H) or {}).get("suitability"),
        extra_fn=lambda data: {
            k: v for k, v in (data.get(SENSOR_FORECAST_SLOT_48H) or {}).items() if k != "suitability"
        },
    ),
    LawnVisionSensorDescription(
        key=SENSOR_FORECAST_SLOT_3D,
        translation_key=SENSOR_FORECAST_SLOT_3D,
        icon="mdi:clock-outline",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (data.get(SENSOR_FORECAST_SLOT_3D) or {}).get("suitability"),
        extra_fn=lambda data: {
            k: v for k, v in (data.get(SENSOR_FORECAST_SLOT_3D) or {}).items() if k != "suitability"
        },
    ),
    LawnVisionSensorDescription(
        key=SENSOR_ACTION_MOW,
        translation_key=SENSOR_ACTION_MOW,
        icon="mdi:robot-mower",
        device_class=SensorDeviceClass.ENUM,
        options=ACTION_STATE_OPTIONS,
        value_fn=_action_state(SENSOR_ACTION_MOW),
        extra_fn=_action_extras(SENSOR_ACTION_MOW),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_ACTION_WATER,
        translation_key=SENSOR_ACTION_WATER,
        icon="mdi:watering-can-outline",
        device_class=SensorDeviceClass.ENUM,
        options=ACTION_STATE_OPTIONS,
        value_fn=_action_state(SENSOR_ACTION_WATER),
        extra_fn=_action_extras(SENSOR_ACTION_WATER),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_ACTION_FERTILIZE,
        translation_key=SENSOR_ACTION_FERTILIZE,
        icon="mdi:bottle-tonic-outline",
        device_class=SensorDeviceClass.ENUM,
        options=ACTION_STATE_OPTIONS,
        value_fn=_action_state(SENSOR_ACTION_FERTILIZE),
        extra_fn=_action_extras(SENSOR_ACTION_FERTILIZE),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_ACTION_SCARIFY,
        translation_key=SENSOR_ACTION_SCARIFY,
        icon="mdi:rake",
        device_class=SensorDeviceClass.ENUM,
        options=ACTION_STATE_OPTIONS,
        value_fn=_action_state(SENSOR_ACTION_SCARIFY),
        extra_fn=_action_extras(SENSOR_ACTION_SCARIFY),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_ACTION_AERATE,
        translation_key=SENSOR_ACTION_AERATE,
        icon="mdi:dots-grid",
        device_class=SensorDeviceClass.ENUM,
        options=ACTION_STATE_OPTIONS,
        value_fn=_action_state(SENSOR_ACTION_AERATE),
        extra_fn=_action_extras(SENSOR_ACTION_AERATE),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_ACTION_OVERSEED,
        translation_key=SENSOR_ACTION_OVERSEED,
        icon="mdi:seed-outline",
        device_class=SensorDeviceClass.ENUM,
        options=ACTION_STATE_OPTIONS,
        value_fn=_action_state(SENSOR_ACTION_OVERSEED),
        extra_fn=_action_extras(SENSOR_ACTION_OVERSEED),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_NEXT_ACTION,
        translation_key=SENSOR_NEXT_ACTION,
        icon="mdi:lightbulb-on-outline",
        device_class=SensorDeviceClass.ENUM,
        options=NEXT_ACTION_OPTIONS,
        value_fn=lambda data: data.get(SENSOR_NEXT_ACTION),
        extra_fn=_next_action_extras,
    ),
    LawnVisionSensorDescription(
        key=SENSOR_CARE_PLAN_7D,
        translation_key=SENSOR_CARE_PLAN_7D,
        icon="mdi:calendar-week-outline",
        native_unit_of_measurement="d",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (data.get(SENSOR_CARE_PLAN_7D) or {}).get("actionable"),
        extra_fn=lambda data: {
            k: v for k, v in (data.get(SENSOR_CARE_PLAN_7D) or {}).items() if k != "actionable"
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lawn Vision sensors."""
    coordinator: LawnVisionCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        LawnVisionSensor(coordinator, entry, description) for description in SENSORS
    )


class LawnVisionSensor(CoordinatorEntity[LawnVisionCoordinator], SensorEntity):
    """A Lawn Vision sensor."""

    entity_description: LawnVisionSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LawnVisionCoordinator,
        entry: ConfigEntry,
        description: LawnVisionSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=coordinator.data.get("name", "Lawn Vision"),
            manufacturer="Lawn Vision",
            model="Local lawn advisor",
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional sensor attributes."""
        if self.entity_description.extra_fn is None:
            return None
        return self.entity_description.extra_fn(self.coordinator.data)
