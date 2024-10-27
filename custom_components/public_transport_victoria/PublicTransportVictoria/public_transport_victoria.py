"""Public Transport Victoria API connector."""
from dataclasses import dataclass
from homeassistant.core import HomeAssistant

import datetime
from homeassistant.util.dt import get_time_zone
import logging

from .api.client import PTVApiClient
from .api.departures import DeparturesAPI, DepartureRequest
from .api.directions import DirectionsAPI
from .api.disruptions import DisruptionsAPI
from .api.patterns import PatternsAPI
from .api.routes import RoutesAPI
from .api.route_types import RouteTypesAPI
from .api.runs import RunsAPI
from .api.stops import StopsAPI

_LOGGER = logging.getLogger(__name__)

@dataclass
class PTVApi:
    """Public Transport Victoria connector."""

    hass: HomeAssistant
    dev_id: str
    api_key: str

    def __init__(self, hass: HomeAssistant, dev_id: str, api_key: str):
        """Initialize."""
        self.hass = hass
        self.client = PTVApiClient(hass, dev_id, api_key)
        self.departures_api = DeparturesAPI(self.client)
        self.directions_api = DirectionsAPI(self.client)
        self.disruptions_api = DisruptionsAPI(self.client)
        self.patterns_api = PatternsAPI(self.client)
        self.routes_api = RoutesAPI(self.client)
        self.route_types_api = RouteTypesAPI(self.client)
        self.runs_api = RunsAPI(self.client)
        self.stops_api = StopsAPI(self.client)

        # These will be set later in async_setup_entry
        self.route_type = None
        self.stop = None
        self.route = None
        self.direction = None

    async def async_get_departures(self):
        """Get departures for the configured stop and route."""
        try:
            _LOGGER.debug(f"Fetching departures with parameters: route_type={self.route_type}, stop={self.stop}, route={self.route}, direction={self.direction}")
            
            request = DepartureRequest(
                route_type=int(self.route_type),
                stop_id=int(self.stop),
                route_id=int(self.route) if self.route else None,
                direction_id=int(self.direction) if self.direction else None,
                max_results=5,
                include_cancelled=False,
                expand=["All"]
            )
            # _LOGGER.debug(f"Departure request: {request}")
            response = await self.departures_api.get_departures(request)
            # _LOGGER.debug(f"Raw API response: {response}")
            
            departures = []
            for departure in response.get("departures", []):
                _LOGGER.debug(f"Processing departure: {departure}")
                departure_time = departure.get("estimated_departure_utc") or departure.get("scheduled_departure_utc")
                if departure_time:
                    departures.append({
                        "departure": self._convert_utc_to_local(departure_time),
                        "platform": departure.get("platform_number"),
                        "direction": departure.get("direction", {}).get("direction_name"),
                    })
            
            _LOGGER.debug(f"Processed departures: {departures}")
            return departures
        except Exception as e:
            _LOGGER.error(f"Error in async_get_departures: {e}", exc_info=True)
            raise
    
    # async def get_route_types(self):
    #     """Get route types."""
    #     return await self.route_types_api.get_route_types()

    def _convert_utc_to_local(self, utc_time: str) -> str:
        """Convert UTC to Home Assistant local time."""
        d = datetime.datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%SZ")
        local_tz = get_time_zone(self.hass.config.time_zone)
        d = d.replace(tzinfo=datetime.timezone.utc).astimezone(local_tz)
        return d.strftime("%Y-%m-%dT%H:%M:%S%z")

# Export PTVApi and PTVApiClient if needed elsewhere
__all__ = ['PTVApi', 'PTVApiClient']




