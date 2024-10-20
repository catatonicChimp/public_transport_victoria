"""Public Transport Victoria Patterns API."""
from dataclasses import dataclass
from typing import Optional
from .client import PTVApiClient

@dataclass
class PatternRequest:
    """Pattern request parameters."""
    run_id: int
    route_type: int
    expand: Optional[list] = None

class PatternsAPI:
    """Patterns API client."""

    def __init__(self, client: PTVApiClient):
        """Initialize the Patterns API client."""
        self.client = client

    async def get_pattern(self, request: PatternRequest):
        """Get the stopping pattern for a specific run in a route."""
        path = f"/v3/pattern/run/{request.run_id}/route_type/{request.route_type}"
        params = {"expand": ",".join(request.expand) if request.expand else None}
        return await self.client.get(path, params=params)
