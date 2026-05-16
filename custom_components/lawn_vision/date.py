"""Native lawn journal: writable date entities for last-done tracking."""

from __future__ import annotations

from datetime import date as date_cls

from homeassistant.components.date import DateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    ACTION_AERATE,
    ACTION_FERTILIZE,
    ACTION_MOW,
    ACTION_OVERSEED,
    ACTION_SCARIFY,
    ACTION_WATER,
    DOMAIN,
)
from .coordinator import LawnVisionCoordinator

JOURNAL_KEYS: dict[str, str] = {
    ACTION_MOW: "last_mow",
    ACTION_WATER: "last_water",
    ACTION_FERTILIZE: "last_fertilize",
    ACTION_SCARIFY: "last_scarify",
    ACTION_AERATE: "last_aerate",
    ACTION_OVERSEED: "last_overseed",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the lawn journal date entities."""
    coordinator: LawnVisionCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        LawnJournalDate(coordinator, entry, action, slug)
        for action, slug in JOURNAL_KEYS.items()
    )


class LawnJournalDate(DateEntity, RestoreEntity):
    """A writable date entity that records when a care action was last done."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-edit-outline"

    def __init__(
        self,
        coordinator: LawnVisionCoordinator,
        entry: ConfigEntry,
        action: str,
        slug: str,
    ) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self.action = action
        self._slug = slug
        self._value: date_cls | None = None
        self._attr_unique_id = f"{entry.entry_id}_{slug}"
        self._attr_translation_key = slug
        device_name = (
            coordinator.data.get("name", "Lawn Vision")
            if coordinator.data
            else "Lawn Vision"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=device_name,
            manufacturer="Lawn Vision",
            model="Local lawn advisor",
        )

    @property
    def native_value(self) -> date_cls | None:
        return self._value

    async def async_set_value(self, value: date_cls) -> None:
        self._value = value
        self.async_write_ha_state()
        self._coordinator.journal[self.action] = value.isoformat()
        await self._coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable", ""):
            try:
                self._value = date_cls.fromisoformat(last_state.state)
                self._coordinator.journal[self.action] = last_state.state
            except ValueError:
                pass
