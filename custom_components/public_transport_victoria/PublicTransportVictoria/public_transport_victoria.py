"""Public Transport Victoria API connector."""
from dataclasses import dataclass
from homeassistant.core import HomeAssistant

import datetime
from homeassistant.util.dt import get_time_zone

from .api.client import PTVApiClient
from .api.departures import DeparturesAPI
from .api.directions import DirectionsAPI
from .api.disruptions import DisruptionsAPI
from .api.patterns import PatternsAPI
from .api.routes import RoutesAPI
from .api.route_types import RouteTypesAPI
from .api.runs import RunsAPI
from .api.stops import StopsAPI

@dataclass
class PTVApi:
    """Public Transport Victoria connector."""

    hass: HomeAssistant
    dev_id: str
    api_key: str

    def __post_init__(self):
        """Initialize API clients."""
        self.client = PTVApiClient(self.hass, self.dev_id, self.api_key)
        self.departures_api = DeparturesAPI(self.client)
        self.directions_api = DirectionsAPI(self.client)
        self.disruptions_api = DisruptionsAPI(self.client)
        self.patterns_api = PatternsAPI(self.client)
        self.routes_api = RoutesAPI(self.client)
        self.route_types_api = RouteTypesAPI(self.client)
        self.runs_api = RunsAPI(self.client)
        self.stops_api = StopsAPI(self.client)

    async def async_get_departures(self):
        """Get departures for the configured stop and route."""
        request = DepartureRequest(
            route_type=int(self.route_type),
            stop_id=int(self.stop),
            route_id=int(self.route) if self.route else None,
            direction_id=int(self.direction) if self.direction else None,
            max_results=5,
            include_cancelled=False,
            expand=["All"]
        )
        
        response = await self.departures_api.get_departures(request)
        
        departures = []
        for departure in response.get("departures", []):
            departure_time = departure.get("estimated_departure_utc") or departure.get("scheduled_departure_utc")
            if departure_time:
                departures.append({
                    "departure": self._convert_utc_to_local(departure_time),
                    "platform": departure.get("platform_number"),
                    "direction": departure.get("direction", {}).get("direction_name"),
                })
        
        return departures
    
    async def get_route_types(self):
        """Get route types."""
        return await self.route_types_api.get_route_types()

    def _convert_utc_to_local(self, utc_time: str) -> str:
        """Convert UTC to Home Assistant local time."""
        d = datetime.datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%SZ")
        local_tz = get_time_zone(self.hass.config.time_zone)
        d = d.replace(tzinfo=datetime.timezone.utc).astimezone(local_tz)
        return d.strftime("%I:%M %p")

# Export PTVApi and PTVApiClient if needed elsewhere
__all__ = ['PTVApi', 'PTVApiClient']


