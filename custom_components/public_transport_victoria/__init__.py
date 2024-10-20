"""
Custom integration to integrate Public Transport Victoria with Home Assistant.
"""
import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .PublicTransportVictoria.public_transport_victoria import PTVApi
from .const import (
    DOMAIN, PLATFORMS, CONF_DEV_ID, CONF_API_KEY, CONF_ROUTE_TYPE, CONF_ROUTE,
    CONF_DIRECTION, CONF_STOP, CONF_ROUTE_TYPE_NAME, CONF_ROUTE_NAME,
    CONF_DIRECTION_NAME, CONF_STOP_NAME
)

SCAN_INTERVAL = timedelta(seconds=30)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info("Starting setup of Public Transport Victoria integration")

    dev_id = entry.data.get(CONF_DEV_ID)
    api_key = entry.data.get(CONF_API_KEY)

    api = PTVApi(
        hass,
        dev_id,
        api_key,
        entry.data[CONF_ROUTE_TYPE],
        entry.data[CONF_ROUTE],
        entry.data[CONF_DIRECTION],
        entry.data[CONF_STOP],
        entry.data[CONF_ROUTE_TYPE_NAME],
        entry.data[CONF_ROUTE_NAME],
        entry.data[CONF_DIRECTION_NAME],
        entry.data[CONF_STOP_NAME],
    )

    coordinator = PTVDataUpdateCoordinator(hass, api=api)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    entry.add_update_listener(async_reload_entry)
    return True


class PTVDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, api: PTVApi) -> None:
        """Initialize."""
        self.api = api
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.api.async_get_data()
        except Exception as exception:
            raise UpdateFailed() from exception


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    unloaded = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
