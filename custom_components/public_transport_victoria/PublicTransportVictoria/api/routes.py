"""Public Transport Victoria Routes API."""
from dataclasses import dataclass
from typing import Optional, List
from .client import PTVApiClient

@dataclass
class RouteRequest:
    """Route request parameters."""
    route_types: Optional[List[int]] = None
    route_name: Optional[str] = None

class RoutesAPI:
    """Routes API client."""

    def __init__(self, client: PTVApiClient):
        """Initialize the Routes API client."""
        self.client = client

    async def get_all_routes(self, request: RouteRequest):
        """View all routes."""
        path = "/v3/routes"
        params = {}
        if request.route_types:
            params["route_types"] = ",".join(map(str, request.route_types))
        if request.route_name:
            params["route_name"] = request.route_name
        return await self.client.get(path, params=params)

    async def get_route_by_id(self, route_id: int):
        """View route by ID."""
        path = f"/v3/routes/{route_id}"
        return await self.client.get(path)
