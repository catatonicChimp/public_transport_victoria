"""Public Transport Victoria Directions API."""
from dataclasses import dataclass
from typing import Optional
from .client import PTVApiClient

@dataclass
class DirectionRequest:
    """Direction request parameters."""
    route_id: int

class DirectionsAPI:
    """Directions API client."""

    def __init__(self, client: PTVApiClient):
        """Initialize the Directions API client."""
        self.client = client

    async def get_directions_for_route(self, request: DirectionRequest):
        """Get directions that a route travels in."""
        path = f"/v3/directions/route/{request.route_id}"
        return await self.client.get(path)

    async def get_direction_by_id(self, direction_id: int):
        """View all routes for a direction of travel."""
        path = f"/v3/directions/{direction_id}"
        return await self.client.get(path)

    async def get_direction_for_route_and_type(self, direction_id: int, route_type: int):
        """View all routes of a particular type for a direction of travel."""
        path = f"/v3/directions/{direction_id}/route_type/{route_type}"
        return await self.client.get(path)
