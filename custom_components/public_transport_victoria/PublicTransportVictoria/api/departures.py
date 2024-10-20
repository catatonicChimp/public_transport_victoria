"""Public Transport Victoria Departures API."""
from dataclasses import dataclass
from typing import List, Optional
from .client import PTVApiClient

@dataclass
class DepartureRequest:
    """Departure request parameters."""
    route_type: int
    stop_id: int
    route_id: Optional[int] = None
    direction_id: Optional[int] = None
    max_results: Optional[int] = None
    include_cancelled: Optional[bool] = None
    expand: Optional[List[str]] = None

class DeparturesAPI:
    """Departures API client."""

    def __init__(self, client: PTVApiClient):
        """Initialize the Departures API client."""
        self.client = client

    async def get_departures(self, request: DepartureRequest):
        """Get departures for a stop."""
        path = f"/v3/departures/route_type/{request.route_type}/stop/{request.stop_id}"
        if request.route_id:
            path += f"/route/{request.route_id}"
        
        params = {
            "direction_id": request.direction_id,
            "max_results": request.max_results,
            "include_cancelled": request.include_cancelled,
            "expand": ",".join(request.expand) if request.expand else None,
        }
        
        return await self.client.get(path, params=params)

# Add more methods for other departure-related endpoints
