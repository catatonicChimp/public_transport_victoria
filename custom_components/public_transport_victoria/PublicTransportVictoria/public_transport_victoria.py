"""Public Transport Victoria API connector."""
from dataclasses import dataclass
from homeassistant.core import HomeAssistant

import datetime
from homeassistant.util.dt import get_time_zone
import logging

from .api.client import PTVApiClient
from .api.departures import DeparturesAPI, DepartureRequest
from .api.directions import DirectionsAPI, DirectionRequest
from .api.disruptions import DisruptionsAPI
from .api.patterns import PatternsAPI
from .api.routes import RoutesAPI
from .api.route_types import RouteTypesAPI
from .api.runs import RunsAPI, RunRequest
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
            
            # Get disruptions for this route and stop
            disruptions = {}
            if self.route:
                try:
                    disruption_response = await self.disruptions_api.get_disruptions_by_route_and_stop(
                        route_id=int(self.route),
                        stop_id=int(self.stop),
                        # disruption_status="current"
                    )
                    disruptions = disruption_response.get("disruptions", {})
                    _LOGGER.debug(f"Disruptions: {disruptions}")
                except Exception as e:
                    _LOGGER.warning(f"Error fetching disruptions: {e}")
            
            departures = []
            for departure in response.get("departures", []):
                _LOGGER.debug(f"Processing departure: {departure}")
                departure_time = departure.get("estimated_departure_utc") or departure.get("scheduled_departure_utc")
                if departure_time:
                    # Get direction information
                    direction_name = None
                    route_id = departure.get("route_id")
                    direction_id = departure.get("direction_id")
                    
                    if route_id and direction_id:
                        try:
                            direction_request = DirectionRequest(route_id=int(route_id))
                            directions_response = await self.directions_api.get_directions_for_route(direction_request)
                            
                            # Find matching direction
                            for direction in directions_response.get("directions", []):
                                if direction.get("direction_id") == direction_id:
                                    direction_name = direction.get("direction_name")
                                    break
                        except Exception as e:
                            _LOGGER.warning(f"Error fetching direction information: {e}")
                    
                    # Process disruptions for this departure
                    departure_disruptions = []
                    disruption_ids = departure.get("disruption_ids", [])
                    if disruption_ids:
                        _LOGGER.debug(f"Processing disruptions for departure. IDs: {disruption_ids}")
                        for disruption_id in disruption_ids:
                            _LOGGER.debug(f"Processing disruption ID: {disruptions}")
                            disruption = disruptions.get(disruption_id)
                            if disruption:
                                departure_disruptions.append({
                                    "title": disruption.get("title"),
                                    "description": disruption.get("description"),
                                    "type": disruption.get("disruption_type"),
                                    "status": disruption.get("disruption_status")
                                })
                        if not departure_disruptions:
                            _LOGGER.debug(f"No matching disruptions found for IDs: {disruption_ids}")
                    
                    # Get vehicle position if run_id is available
                    vehicle_position = None
                    run_id = departure.get("run_id")
                    _LOGGER.debug(f"Run ID: {run_id}")
                    if run_id:
                        vehicle_position = await self.get_vehicle_position(run_id)
                    
                    departures.append({
                        "departure": self._convert_utc_to_local(departure_time),
                        "platform": departure.get("platform_number"),
                        "direction": direction_name or departure.get("direction", {}).get("direction_name"),
                        "disruptions": departure_disruptions,
                        "vehicle_position": vehicle_position
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

    async def get_vehicle_position(self, run_id: int):
        """Get the current position of a vehicle for a specific run."""
        try:
            if not self.route_type:
                _LOGGER.error("Route type not set")
                return None

            request = RunRequest(run_id=run_id, route_type=int(self.route_type))

            position = await self.runs_api.get_vehicle_position(request)

            if position:
                _LOGGER.debug(f"Vehicle position for run {run_id}: {position}")
                return position
            else:
                _LOGGER.debug(f"No vehicle position available for run {run_id}")
                return None

        except Exception as e:
            _LOGGER.error(f"Error getting vehicle position: {e}", exc_info=True)
            return None

# Export PTVApi and PTVApiClient if needed elsewhere
__all__ = ['PTVApi', 'PTVApiClient']




