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
    DOMAIN,
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
from .coordinator import LawnVisionCoordinator


@dataclass(frozen=True, kw_only=True)
class LawnVisionSensorDescription(SensorEntityDescription):
    """Description for a Lawn Vision sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    extra_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


SENSORS: tuple[LawnVisionSensorDescription, ...] = (
    LawnVisionSensorDescription(
        key=SENSOR_PHASE,
        translation_key=SENSOR_PHASE,
        icon="mdi:grass",
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
        value_fn=lambda data: data.get(SENSOR_FORECAST_GROWTH_TREND),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_FORECAST_BEST_WINDOW,
        translation_key=SENSOR_FORECAST_BEST_WINDOW,
        icon="mdi:calendar-clock",
        value_fn=lambda data: data.get(SENSOR_FORECAST_BEST_WINDOW),
    ),
    LawnVisionSensorDescription(
        key=SENSOR_FORECAST_CARE_HINT,
        translation_key=SENSOR_FORECAST_CARE_HINT,
        icon="mdi:calendar-check-outline",
        value_fn=lambda data: data.get(SENSOR_FORECAST_CARE_HINT),
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
