"""Public Transport Victoria Disruptions API."""
from dataclasses import dataclass
from typing import List, Optional
from .client import PTVApiClient

@dataclass
class DisruptionRequest:
    """Disruption request parameters."""
    route_types: Optional[List[int]] = None
    disruption_modes: Optional[List[int]] = None
    disruption_status: Optional[str] = None

class DisruptionsAPI:
    """Disruptions API client."""

    def __init__(self, client: PTVApiClient):
        """Initialize the Disruptions API client."""
        self.client = client

    async def get_all_disruptions(self, request: DisruptionRequest):
        """View all disruptions for all route types."""
        path = "/v3/disruptions"
        params = {
            "route_types": ",".join(map(str, request.route_types)) if request.route_types else None,
            "disruption_modes": ",".join(map(str, request.disruption_modes)) if request.disruption_modes else None,
            "disruption_status": request.disruption_status,
        }
        return await self.client.get(path, params=params)

    async def get_disruptions_by_route(self, route_id: int, disruption_status: Optional[str] = None):
        """View all disruptions for a particular route."""
        path = f"/v3/disruptions/route/{route_id}"
        params = {"disruption_status": disruption_status}
        return await self.client.get(path, params=params)

    async def get_disruptions_by_route_and_stop(self, route_id: int, stop_id: int, disruption_status: Optional[str] = None):
        """View all disruptions for a particular route and stop."""
        path = f"/v3/disruptions/route/{route_id}/stop/{stop_id}"
        params = {"disruption_status": disruption_status}
        return await self.client.get(path, params=params)

    async def get_disruptions_by_stop(self, stop_id: int, disruption_status: Optional[str] = None):
        """View all disruptions for a particular stop."""
        path = f"/v3/disruptions/stop/{stop_id}"
        params = {"disruption_status": disruption_status}
        return await self.client.get(path, params=params)

    async def get_disruption_by_id(self, disruption_id: int):
        """View a specific disruption."""
        path = f"/v3/disruptions/{disruption_id}"
        return await self.client.get(path)

    async def get_disruption_modes(self):
        """Get all disruption modes."""
        path = "/v3/disruptions/modes"
        return await self.client.get(path)
