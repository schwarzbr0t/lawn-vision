"""Config flow for Lawn Vision."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import (
    CONF_AREA_M2,
    CONF_ESTIMATE_FROM_WEATHER,
    CONF_GDD_ENTITY,
    CONF_GRASS_TYPE,
    CONF_GTS_ENTITY,
    CONF_HUMIDITY_ENTITY,
    CONF_LAST_AERATE_ENTITY,
    CONF_LAST_FERTILIZE_ENTITY,
    CONF_LAST_MOW_ENTITY,
    CONF_LAST_OVERSEED_ENTITY,
    CONF_LAST_SCARIFY_ENTITY,
    CONF_LAST_WATER_ENTITY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MEAN_DAILY_TEMPERATURE_ENTITY,
    CONF_MOISTURE_10CM_ENTITY,
    CONF_MOISTURE_20CM_ENTITY,
    CONF_MOISTURE_30CM_ENTITY,
    CONF_MOISTURE_ENTITY,
    CONF_RAIN_ENTITY,
    CONF_SOIL_TEMPERATURE_ENTITY,
    CONF_TEMPERATURE_ENTITY,
    CONF_USE_OPEN_METEO,
    CONF_WEATHER_ENTITY,
    DEFAULT_AREA_M2,
    DEFAULT_GRASS_TYPE,
    DEFAULT_NAME,
    DOMAIN,
    GRASS_TYPES,
)

LOGGER = logging.getLogger(__name__)

# (config-key, entity-domain) for every optional entity selector.
_ENTITY_FIELDS: tuple[tuple[str, str], ...] = (
    (CONF_WEATHER_ENTITY, "weather"),
    (CONF_TEMPERATURE_ENTITY, "sensor"),
    (CONF_MEAN_DAILY_TEMPERATURE_ENTITY, "sensor"),
    (CONF_SOIL_TEMPERATURE_ENTITY, "sensor"),
    (CONF_HUMIDITY_ENTITY, "sensor"),
    (CONF_MOISTURE_ENTITY, "sensor"),
    (CONF_MOISTURE_10CM_ENTITY, "sensor"),
    (CONF_MOISTURE_20CM_ENTITY, "sensor"),
    (CONF_MOISTURE_30CM_ENTITY, "sensor"),
    (CONF_RAIN_ENTITY, "sensor"),
    (CONF_GTS_ENTITY, "sensor"),
    (CONF_GDD_ENTITY, "sensor"),
    (CONF_LAST_MOW_ENTITY, "input_datetime"),
    (CONF_LAST_WATER_ENTITY, "input_datetime"),
    (CONF_LAST_FERTILIZE_ENTITY, "input_datetime"),
    (CONF_LAST_SCARIFY_ENTITY, "input_datetime"),
    (CONF_LAST_AERATE_ENTITY, "input_datetime"),
    (CONF_LAST_OVERSEED_ENTITY, "input_datetime"),
)


def _clean_defaults(defaults: dict[str, Any] | None) -> dict[str, Any]:
    """Strip ``None`` and empty strings — HA's frontend rejects either as a
    selector default with a generic ``400: Bad Request``."""
    if not defaults:
        return {}
    return {k: v for k, v in defaults.items() if v not in (None, "")}


def _opt(key: str, defaults: dict[str, Any]) -> vol.Optional:
    """``vol.Optional`` with a default *only* when we actually have a value."""
    if key in defaults:
        return vol.Optional(key, default=defaults[key])
    return vol.Optional(key)


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the setup / options form schema."""
    d = _clean_defaults(defaults)

    fields: dict[Any, Any] = {
        vol.Optional(CONF_NAME, default=d.get(CONF_NAME, DEFAULT_NAME)): str,
        vol.Optional(
            CONF_USE_OPEN_METEO, default=d.get(CONF_USE_OPEN_METEO, False)
        ): bool,
        vol.Optional(
            CONF_ESTIMATE_FROM_WEATHER,
            default=d.get(CONF_ESTIMATE_FROM_WEATHER, False),
        ): bool,
        # Lat/Lon as plain coerced floats. NumberSelector with a float step
        # historically tripped HA's schema serializer and showed up as a bare
        # "400: Bad Request" in the frontend — keep this dead simple.
        _opt(CONF_LATITUDE, d): vol.Coerce(float),
        _opt(CONF_LONGITUDE, d): vol.Coerce(float),
        vol.Optional(
            CONF_AREA_M2, default=d.get(CONF_AREA_M2, DEFAULT_AREA_M2)
        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=5000)),
        vol.Optional(
            CONF_GRASS_TYPE,
            default=d.get(CONF_GRASS_TYPE, DEFAULT_GRASS_TYPE),
        ): SelectSelector(
            SelectSelectorConfig(
                options=list(GRASS_TYPES), translation_key=CONF_GRASS_TYPE
            )
        ),
    }

    for key, domain in _ENTITY_FIELDS:
        fields[_opt(key, d)] = EntitySelector(EntitySelectorConfig(domain=domain))

    return vol.Schema(fields)


class LawnVisionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lawn Vision."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            await self.async_set_unique_id(user_input.get(CONF_NAME, DEFAULT_NAME))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, DEFAULT_NAME),
                data=user_input,
            )

        return self.async_show_form(step_id="user", data_schema=_schema())

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return LawnVisionOptionsFlow(config_entry)


class LawnVisionOptionsFlow(config_entries.OptionsFlow):
    """Handle Lawn Vision options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        # Private attribute so we work on HA < 2024.11 (no auto-inject) *and*
        # on newer HA (deprecation warning when assigning ``self.config_entry``).
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {**self._entry.data, **self._entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(defaults))
