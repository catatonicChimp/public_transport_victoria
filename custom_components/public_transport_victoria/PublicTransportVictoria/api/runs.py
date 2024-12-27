"""Public Transport Victoria Runs API."""

from dataclasses import dataclass
from typing import Optional
from .client import PTVApiClient


@dataclass
class RunRequest:
    """Run request parameters."""

    route_type: int
    route_id: Optional[int] = None
    run_id: Optional[int] = None
    expand: Optional[list[str]] = (
        None  # All, VehiclePosition, VehicleDescriptor, or None
    )
    date_utc: Optional[str] = None  # ISO 8601 UTC format
    include_geopath: Optional[bool] = None


class RunsAPI:
    """Runs API client."""

    def __init__(self, client: PTVApiClient):
        """Initialize the Runs API client."""
        self.client = client

    def _build_params(self, request: RunRequest) -> dict:
        """Build query parameters from request object."""
        params = {}
        if request.expand:
            params["expand"] = ",".join(request.expand)
        if request.date_utc:
            params["date_utc"] = request.date_utc
        if request.include_geopath is not None:
            params["include_geopath"] = request.include_geopath
        return params

    async def get_runs_for_route(self, request: RunRequest):
        """Get all runs for a specific route."""
        if not request.route_id:
            raise ValueError("route_id is required")

        path = f"/v3/runs/route/{request.route_id}/route_type/{request.route_type}"
        params = self._build_params(request)
        return await self.client.get(path, params=params)

    async def get_run_by_id(self, request: RunRequest):
        """Get a single run by ID."""
        if not request.run_id:
            raise ValueError("run_id is required")

        path = f"/v3/runs/{request.run_id}/route_type/{request.route_type}"
        params = self._build_params(request)
        return await self.client.get(path, params=params)

    async def get_vehicle_position(self, request: RunRequest):
        """Get the current vehicle position for a specific run."""
        if not request.run_id:
            raise ValueError("run_id is required")

        # Ensure VehiclePosition is included in expand
        if not request.expand:
            request.expand = ["VehiclePosition"]
        elif "VehiclePosition" not in request.expand:
            request.expand.append("VehiclePosition")

        response = await self.get_run_by_id(request)
        if response and "runs" in response:
            runs = response["runs"]
            if runs and isinstance(runs, list):  # Ensure runs is a non-empty list
                run = runs[0]
                vehicle_position = run.get("vehicle_position")
                if vehicle_position:
                    return {
                        "latitude": vehicle_position.get("latitude"),
                        "longitude": vehicle_position.get("longitude"),
                        "bearing": vehicle_position.get("bearing"),
                        "timestamp": vehicle_position.get("timestamp"),
                    }
        return None
