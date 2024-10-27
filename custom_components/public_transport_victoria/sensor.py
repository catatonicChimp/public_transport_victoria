"""Platform for sensor integration."""

import datetime
import logging

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)
from homeassistant.const import ATTR_ATTRIBUTION
from .const import ATTRIBUTION, DOMAIN, CONF_ROUTE_NAME, CONF_DIRECTION_NAME, CONF_STOP_NAME

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = datetime.timedelta(minutes=10)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add sensors for passed config_entry in HA."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    sensors = []
    for i in range(5):  # Create 5 sensors for the next 5 departures
        sensors.append(PublicTransportVictoriaSensor(coordinator, i, config_entry))

    async_add_entities(sensors, True)


class PublicTransportVictoriaDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Public Transport Victoria data."""

    def __init__(self, hass, connector):
        """Initialize the coordinator."""
        self.connector = connector
        super().__init__(
            hass,
            _LOGGER,
            name="Public Transport Victoria",
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        """Fetch data from Public Transport Victoria."""
        try:
            _LOGGER.debug("Fetching new data from Public Transport Victoria API.")
            await self.connector.async_update()
            return self.connector.departures  # Return the latest data
        except Exception as e:
            _LOGGER.error("Failed to fetch data from Public Transport Victoria: %s", e)
            return []  # Returning empty data set if fetching fails

class PublicTransportVictoriaSensor(CoordinatorEntity, Entity):
    """Representation of a Public Transport Victoria Sensor."""

    def __init__(self, coordinator, index, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._index = index
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_{index}"

    @property
    def name(self):
        """Return the name of the sensor."""
        route_name = self._config_entry.data.get(CONF_ROUTE_NAME, "Unknown Route")
        direction_name = self._config_entry.data.get(CONF_DIRECTION_NAME, "Unknown Direction")
        stop_name = self._config_entry.data.get(CONF_STOP_NAME, "Unknown Stop")
        return f"PTV {route_name} to {direction_name} from {stop_name} ({self._index + 1})"

    @property
    def state(self):
        """Return the state of the sensor."""
        if self.coordinator.data and len(self.coordinator.data) > self._index:
            return self.coordinator.data[self._index].get("departure", "No data")
        return "No data"

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        attrs = {}
        if self.coordinator.data and len(self.coordinator.data) > self._index:
            attrs = self.coordinator.data[self._index].copy()
        attrs[ATTR_ATTRIBUTION] = ATTRIBUTION
        return attrs

    @property
    def device_class(self):
        """Return the device class."""
        return "timestamp"
