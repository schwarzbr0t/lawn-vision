"""Config flow for Lawn Vision."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import (
    CONF_AREA_M2,
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
    GRASS_TYPES,
)


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the setup/options schema."""
    defaults = defaults or {}
    entity_defaults = {
        key: {"default": defaults[key]} if defaults.get(key) else {}
        for key in (
            CONF_WEATHER_ENTITY,
            CONF_TEMPERATURE_ENTITY,
            CONF_MEAN_DAILY_TEMPERATURE_ENTITY,
            CONF_SOIL_TEMPERATURE_ENTITY,
            CONF_HUMIDITY_ENTITY,
            CONF_MOISTURE_ENTITY,
            CONF_MOISTURE_10CM_ENTITY,
            CONF_MOISTURE_20CM_ENTITY,
            CONF_MOISTURE_30CM_ENTITY,
            CONF_RAIN_ENTITY,
            CONF_GTS_ENTITY,
            CONF_GDD_ENTITY,
            CONF_LAST_MOW_ENTITY,
            CONF_LAST_WATER_ENTITY,
            CONF_LAST_FERTILIZE_ENTITY,
            CONF_LAST_SCARIFY_ENTITY,
            CONF_LAST_AERATE_ENTITY,
            CONF_LAST_OVERSEED_ENTITY,
        )
    }

    return vol.Schema(
        {
            vol.Optional(
                CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)
            ): str,
            vol.Optional(CONF_WEATHER_ENTITY, **entity_defaults[CONF_WEATHER_ENTITY]): EntitySelector(
                EntitySelectorConfig(domain="weather")
            ),
            vol.Optional(CONF_TEMPERATURE_ENTITY, **entity_defaults[CONF_TEMPERATURE_ENTITY]): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                CONF_MEAN_DAILY_TEMPERATURE_ENTITY,
                **entity_defaults[CONF_MEAN_DAILY_TEMPERATURE_ENTITY],
            ): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                CONF_SOIL_TEMPERATURE_ENTITY,
                **entity_defaults[CONF_SOIL_TEMPERATURE_ENTITY],
            ): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_HUMIDITY_ENTITY, **entity_defaults[CONF_HUMIDITY_ENTITY]): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_MOISTURE_ENTITY, **entity_defaults[CONF_MOISTURE_ENTITY]): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_MOISTURE_10CM_ENTITY, **entity_defaults[CONF_MOISTURE_10CM_ENTITY]): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_MOISTURE_20CM_ENTITY, **entity_defaults[CONF_MOISTURE_20CM_ENTITY]): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_MOISTURE_30CM_ENTITY, **entity_defaults[CONF_MOISTURE_30CM_ENTITY]): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_RAIN_ENTITY, **entity_defaults[CONF_RAIN_ENTITY]): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_GTS_ENTITY, **entity_defaults[CONF_GTS_ENTITY]): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_GDD_ENTITY, **entity_defaults[CONF_GDD_ENTITY]): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                CONF_AREA_M2, default=defaults.get(CONF_AREA_M2, DEFAULT_AREA_M2)
            ): NumberSelector(
                NumberSelectorConfig(min=1, max=5000, step=1, mode="box")
            ),
            vol.Optional(
                CONF_GRASS_TYPE,
                default=defaults.get(CONF_GRASS_TYPE, DEFAULT_GRASS_TYPE),
            ): SelectSelector(
                SelectSelectorConfig(options=GRASS_TYPES, translation_key=CONF_GRASS_TYPE)
            ),
            vol.Optional(CONF_LAST_MOW_ENTITY, **entity_defaults[CONF_LAST_MOW_ENTITY]): EntitySelector(
                EntitySelectorConfig(domain="input_datetime")
            ),
            vol.Optional(CONF_LAST_WATER_ENTITY, **entity_defaults[CONF_LAST_WATER_ENTITY]): EntitySelector(
                EntitySelectorConfig(domain="input_datetime")
            ),
            vol.Optional(CONF_LAST_FERTILIZE_ENTITY, **entity_defaults[CONF_LAST_FERTILIZE_ENTITY]): EntitySelector(
                EntitySelectorConfig(domain="input_datetime")
            ),
            vol.Optional(CONF_LAST_SCARIFY_ENTITY, **entity_defaults[CONF_LAST_SCARIFY_ENTITY]): EntitySelector(
                EntitySelectorConfig(domain="input_datetime")
            ),
            vol.Optional(CONF_LAST_AERATE_ENTITY, **entity_defaults[CONF_LAST_AERATE_ENTITY]): EntitySelector(
                EntitySelectorConfig(domain="input_datetime")
            ),
            vol.Optional(CONF_LAST_OVERSEED_ENTITY, **entity_defaults[CONF_LAST_OVERSEED_ENTITY]): EntitySelector(
                EntitySelectorConfig(domain="input_datetime")
            ),
        }
    )


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
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {**self._config_entry.data, **self._config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(defaults))
