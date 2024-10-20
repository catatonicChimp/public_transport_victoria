"""Public Transport Victoria RouteTypes API."""
from .client import PTVApiClient

class RouteTypesAPI:
    """RouteTypes API client."""

    def __init__(self, client: PTVApiClient):
        """Initialize the RouteTypes API client."""
        self.client = client

    async def get_route_types(self):
        """Get all route types."""
        path = "/v3/route_types"
        return await self.client.get(path)
