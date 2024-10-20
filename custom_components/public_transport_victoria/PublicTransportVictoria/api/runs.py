"""Public Transport Victoria Runs API."""
from dataclasses import dataclass
from typing import Optional
from .client import PTVApiClient

@dataclass
class RunRequest:
    """Run request parameters."""
    route_id: int
    route_type: int

class RunsAPI:
    """Runs API client."""

    def __init__(self, client: PTVApiClient):
        """Initialize the Runs API client."""
        self.client = client

    async def get_runs_for_route(self, request: RunRequest):
        """Get all runs for a specific route."""
        path = f"/v3/runs/route/{request.route_id}/route_type/{request.route_type}"
        return await self.client.get(path)

    async def get_run_by_id(self, run_id: int, route_type: int):
        """Get a single run by ID."""
        path = f"/v3/runs/{run_id}/route_type/{route_type}"
        return await self.client.get(path)
