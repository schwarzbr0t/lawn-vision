"""Lawn Vision integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import LawnVisionCoordinator

LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.DATE]

CARD_URL = f"/{DOMAIN}/lawn-vision-card.js"
CARD_FILE = "lawn-vision-card.js"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lawn Vision from a config entry."""
    coordinator = LawnVisionCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await _async_register_card(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Second refresh now that the date platform has restored journal entries.
    await coordinator.async_request_refresh()

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the Lovelace card bundled with the integration and auto-load it."""
    if hass.data[DOMAIN].get("_card_registered"):
        return

    # Imports are local so the test suite, which mocks the top-level
    # homeassistant package, does not need to mock these submodules.
    from homeassistant.components.frontend import add_extra_js_url
    from homeassistant.components.http import StaticPathConfig

    www_path = Path(__file__).parent / "www"
    card_path = www_path / CARD_FILE
    if not card_path.is_file():
        LOGGER.warning("Lawn Vision card file missing at %s", card_path)
        return

    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(card_path), True)]
        )
    except RuntimeError:
        # Path already registered (HA reload).
        pass
    except Exception:  # noqa: BLE001
        LOGGER.exception("Failed to register Lawn Vision card static path")
        return

    try:
        add_extra_js_url(hass, CARD_URL)
    except Exception:  # noqa: BLE001
        LOGGER.exception("Failed to add Lawn Vision card to frontend")
        return

    hass.data[DOMAIN]["_card_registered"] = True
    LOGGER.info("Lawn Vision card registered at %s", CARD_URL)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
