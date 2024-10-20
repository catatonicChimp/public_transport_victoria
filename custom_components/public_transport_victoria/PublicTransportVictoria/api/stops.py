"""Public Transport Victoria Stops API."""
from dataclasses import dataclass
from typing import Optional, List
from .client import PTVApiClient

@dataclass
class StopRequest:
    """Stop request parameters."""
    route_id: int
    route_type: int
    stop_disruptions: Optional[bool] = None
    include_geopath: Optional[bool] = None
    geopath_utc: Optional[str] = None
    include_advertised_interchange: Optional[bool] = None

@dataclass
class StopsByDistanceRequest:
    """Stops by distance request parameters."""
    latitude: float
    longitude: float
    route_types: Optional[List[int]] = None
    max_results: Optional[int] = None
    max_distance: Optional[int] = None
    stop_disruptions: Optional[bool] = None

class StopsAPI:
    """Stops API client."""

    def __init__(self, client: PTVApiClient):
        """Initialize the Stops API client."""
        self.client = client

    async def get_stop_by_id(self, stop_id: int, route_type: int, stop_disruptions: Optional[bool] = None):
        """View details of a specific stop."""
        path = f"/v3/stops/{stop_id}/route_type/{route_type}"
        params = {"stop_disruptions": stop_disruptions}
        return await self.client.get(path, params=params)

    async def get_stops_for_route(self, request: StopRequest):
        """View all stops on a specific route."""
        path = f"/v3/stops/route/{request.route_id}/route_type/{request.route_type}"
        params = {
            "stop_disruptions": request.stop_disruptions,
            "include_geopath": request.include_geopath,
            "geopath_utc": request.geopath_utc,
            "include_advertised_interchange": request.include_advertised_interchange,
        }
        return await self.client.get(path, params=params)

    async def get_stops_by_distance(self, request: StopsByDistanceRequest):
        """View all stops near a specific location."""
        path = "/v3/stops/location/{request.latitude},{request.longitude}"
        params = {
            "route_types": ",".join(map(str, request.route_types)) if request.route_types else None,
            "max_results": request.max_results,
            "max_distance": request.max_distance,
            "stop_disruptions": request.stop_disruptions,
        }
        return await self.client.get(path, params=params)
