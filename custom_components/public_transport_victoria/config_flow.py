"""Config flow for Public Transport Victoria integration."""

import logging
import json
import os
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .PublicTransportVictoria.public_transport_victoria import PTVApi
from .PublicTransportVictoria.api.routes import RouteRequest
from .PublicTransportVictoria.api.stops import StopsByDistanceRequest, StopRequest
from .PublicTransportVictoria.api.directions import DirectionRequest
from .const import (
    DOMAIN,
    CONF_DEV_ID,
    CONF_API_KEY,
    CONF_ROUTE_TYPE,
    CONF_STOP_ID,
    CONF_STOP,
    CONF_ROUTE_ID,
    CONF_ROUTE_NAME,
    CONF_DIRECTION_ID,
    CONF_DIRECTION_NAME,
    CONF_ROUTE_TYPE_NAME,
)

_LOGGER = logging.getLogger(__name__)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class PTVConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Public Transport Victoria."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.ptv_api: Optional[PTVApi] = None
        self.data: Dict[str, Any] = {}

    def load_debug_credentials(self) -> Dict[str, str]:
        """Load debug credentials from a file."""
        debug_file = os.path.join(os.path.dirname(__file__), "debug_credentials.json")
        if os.path.exists(debug_file):
            with open(debug_file, "r") as f:
                return json.load(f)
        return {}

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        # Load debug credentials if available
        debug_credentials = self.load_debug_credentials()

        if user_input is None and debug_credentials:
            user_input = debug_credentials

        if user_input is not None:
            try:
                self.ptv_api = PTVApi(
                    self.hass, user_input[CONF_DEV_ID], user_input[CONF_API_KEY]
                )
                # Test the API connection using a simple API call
                route_types = await self.ptv_api.route_types_api.get_route_types()
                if route_types:  # If we get a valid response, consider it a success
                    self.data.update(user_input)
                    return await self.async_step_route_type()
                else:
                    raise CannotConnect
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEV_ID, default=debug_credentials.get(CONF_DEV_ID, "")
                    ): str,
                    vol.Required(
                        CONF_API_KEY, default=debug_credentials.get(CONF_API_KEY, "")
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_route_type(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle route type selection."""
        errors: Dict[str, str] = {}

        route_types = await self.ptv_api.route_types_api.get_route_types()
        route_type_options = {
            str(rt["route_type"]): rt["route_type_name"]
            for rt in route_types["route_types"]
        }

        if user_input is not None:
            selected_route_type = user_input[CONF_ROUTE_TYPE]
            self.data.update(
                {
                    CONF_ROUTE_TYPE: selected_route_type,
                    CONF_ROUTE_TYPE_NAME: route_type_options[selected_route_type],
                }
            )
            return await self.async_step_search_method()

        return self.async_show_form(
            step_id="route_type",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ROUTE_TYPE): vol.In(route_type_options),
                }
            ),
            errors=errors,
        )

    async def async_step_search_method(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle search method selection."""
        errors: Dict[str, str] = {}

        # First, fetch all stations if we haven't already
        if not hasattr(self, "stations"):
            # Melbourne CBD coordinates
            latitude = -37.8136
            longitude = 144.9631
            max_distance = 150000  # 150 km radius to cover the whole network
            max_results = 10000  # Adjust as needed to ensure all stations are included
            request = StopsByDistanceRequest(
                latitude=latitude,
                longitude=longitude,
                route_types=[int(self.data[CONF_ROUTE_TYPE])],
                max_distance=max_distance,
                max_results=max_results,
            )

            try:
                stations = await self.ptv_api.stops_api.get_stops_by_distance(request)
                if stations and "stops" in stations:
                    self.stations = {
                        str(stop["stop_id"]): {
                            "name": stop["stop_name"],
                            "suburb": stop.get("stop_suburb", ""),
                            "latitude": stop["stop_latitude"],
                            "longitude": stop["stop_longitude"],
                        }
                        for stop in stations["stops"]
                    }
                else:
                    errors["base"] = "no_stations_found"
                    return self.async_show_form(step_id="search_method", errors=errors)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
                return self.async_show_form(step_id="search_method", errors=errors)

        # Now that we have the stations, let the user choose a search method
        if user_input is not None:
            search_method = user_input["search_method"]
            _LOGGER.debug(f"Search method: {search_method}")
            if search_method == "line_name":
                return await self.async_step_search_by_line_name()
            elif search_method == "stop_name":
                return await self.async_step_select_station()
            elif search_method == "suburb":
                return await self.async_step_search_by_suburb()
            elif search_method == "map":
                return await self.async_step_search_by_map()

        # If we get here, either it's the first time through or there was an error
        return self.async_show_form(
            step_id="search_method",
            data_schema=vol.Schema(
                {
                    vol.Required("search_method"): vol.In(
                        ["line_name", "stop_name", "suburb", "map"]
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_search_by_line_name(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle search by line name."""
        _LOGGER.debug("IN SEARCH BY LINE NAME")
        errors: Dict[str, str] = {}

        if user_input is not None:
            selected_route_id = user_input["route"]
            selected_route_name = self.routes[selected_route_id]["display_name"]
            self.data[CONF_ROUTE_ID] = selected_route_id
            self.data[CONF_ROUTE_NAME] = selected_route_name
            return await self.async_step_select_station_for_route()

        try:
            route_type = int(self.data[CONF_ROUTE_TYPE])
            route_request = RouteRequest(route_types=[route_type])
            routes = await self.ptv_api.routes_api.get_all_routes(route_request)

            if not routes or "routes" not in routes:
                errors["base"] = "no_routes_found"
                return self.async_show_form(
                    step_id="search_by_line_name",
                    errors=errors,
                )

            self.routes = {}
            route_options = []
            for route in routes["routes"]:
                route_id = str(route["route_id"])
                route_number = route.get("route_number", "")
                route_name = route["route_name"]
                if route_number:
                    display_name = f"{route_number} - {route_name}"
                    try:
                        sort_key = int(route_number)
                    except ValueError:
                        sort_key = (
                            route_number  # fallback to string if not a valid integer
                        )
                else:
                    display_name = route_name
                    sort_key = route_name

                self.routes[route_id] = {
                    "display_name": display_name,
                    "sort_key": sort_key,
                }
                route_options.append((route_id, display_name, sort_key))

            # Sort the routes
            route_options.sort(key=lambda x: (isinstance(x[2], str), x[2]))

            # Create the final sorted dictionary
            sorted_route_options = {
                route_id: display_name for route_id, display_name, _ in route_options
            }

            return self.async_show_form(
                step_id="search_by_line_name",
                data_schema=vol.Schema(
                    {vol.Required("route"): vol.In(sorted_route_options)}
                ),
                errors=errors,
            )

        except Exception as e:
            _LOGGER.error(f"Error fetching routes: {str(e)}")
            errors["base"] = "cannot_fetch_routes"
            return self.async_show_form(
                step_id="search_by_line_name",
                errors=errors,
            )

    async def async_step_search_by_suburb(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle station search by suburb using a dropdown."""
        errors: Dict[str, str] = {}
        print("IN SEARCH BY SUBURB")
        print(user_input)
        if user_input is not None:
            selected_suburb = user_input["suburb"]
            self.filtered_stations = {
                stop_id: details
                for stop_id, details in self.stations.items()
                if details["suburb"].lower() == selected_suburb.lower()
            }
            if self.filtered_stations:
                return await self.async_step_select_station()
            else:
                errors["base"] = "no_stations_found"

        # Get unique suburbs and sort them
        suburbs = sorted(
            set(
                details["suburb"]
                for details in self.stations.values()
                if details["suburb"]
            )
        )

        suburb_options = [
            selector.SelectOptionDict(value=suburb, label=suburb) for suburb in suburbs
        ]

        return self.async_show_form(
            step_id="search_by_suburb",
            data_schema=vol.Schema(
                {
                    vol.Required("suburb"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=suburb_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            custom_value=False,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_search_by_map(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle station search by map."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                latitude = user_input["location"]["latitude"]
                longitude = user_input["location"]["longitude"]
                # Search for stations near these coordinates using the PTV API
                stations = await self.ptv_api.stops_api.search_stops(
                    latitude, longitude
                )
                if stations:
                    self.stations = stations
                    return await self.async_step_select_station()
                else:
                    errors["base"] = "no_stations_found"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="search_by_map",
            data_schema=vol.Schema(
                {
                    vol.Required("location"): selector.LocationSelector(
                        radius=True,
                        icon="mdi:train-station",
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_select_station(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle station selection after suburb selection."""
        errors: Dict[str, str] = {}

        # Ensure we have the stations data
        if not hasattr(self, "filtered_stations"):
            # If we don't have filtered stations, we need to go back to the suburb selection step
            return await self.async_step_search_by_suburb()

        if user_input is not None and "station" in user_input:
            station_id = user_input["station"]
            if station_id in self.filtered_stations:
                self.data[CONF_STOP] = self.filtered_stations[station_id]
                self.data[CONF_STOP_ID] = station_id
                return await self.async_step_route()
            else:
                errors["base"] = "invalid_station"

        station_options = [
            selector.SelectOptionDict(
                value=stop_id, label=f"{details['name']} ({details['suburb']})"
            )
            for stop_id, details in sorted(
                self.filtered_stations.items(), key=lambda x: x[1]["name"]
            )
        ]

        return self.async_show_form(
            step_id="select_station",
            data_schema=vol.Schema(
                {
                    vol.Required("station"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=station_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            custom_value=False,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_route(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle route and direction selection."""
        errors: Dict[str, str] = {}
        _LOGGER.debug(f"IN ROUTE - Data: {self.data}, User Input: {user_input}")

        if user_input is not None:
            self.data[CONF_DIRECTION_ID] = user_input["route_direction"]
            self.data[CONF_DIRECTION_NAME] = self.directions[
                user_input["route_direction"]
            ]
            return await self.async_step_final_config()

        selected_stop_id = self.data[CONF_STOP_ID]
        route_type = int(self.data[CONF_ROUTE_TYPE])
        pre_selected_route_id = self.data.get(CONF_ROUTE_ID)

        try:
            stop_details = await self.ptv_api.stops_api.get_stop_by_id(
                selected_stop_id, route_type
            )
            _LOGGER.debug(f"Stop details: {stop_details}")

            if "stop" not in stop_details or "routes" not in stop_details["stop"]:
                errors["base"] = "no_routes_found"
                return self.async_show_form(step_id="route", errors=errors)

            route_direction_options = []
            for route in stop_details["stop"]["routes"]:
                if not isinstance(route, dict):
                    _LOGGER.warning(f"Unexpected route data type: {type(route)}")
                    continue

                route_id = route.get("route_id")
                if route_id is None:
                    _LOGGER.warning(f"Missing route_id for route: {route}")
                    continue

                # Skip if we have a pre-selected route and it doesn't match
                if pre_selected_route_id and str(route_id) != str(
                    pre_selected_route_id
                ):
                    continue

                route_number = route.get("route_number", "")
                route_name = route.get("route_name", "")
                self.directions = {}
                try:
                    direction_request = DirectionRequest(route_id=int(route_id))
                    directions = (
                        await self.ptv_api.directions_api.get_directions_for_route(
                            direction_request
                        )
                    )
                    _LOGGER.debug(f"Directions for route {route_id}: {directions}")

                    for direction in directions.get("directions", []):
                        direction_id = str(direction.get("direction_id", ""))
                        direction_name = direction.get("direction_name", "")
                        self.directions[direction_id] = direction_name
                        if route_number:
                            route_display = f"Route {route_number}: {route_name}"
                        else:
                            route_display = route_name

                        option_value = f"{direction_id}"
                        option_label = f"{route_display} - {direction_name}"

                        route_direction_options.append(
                            selector.SelectOptionDict(
                                value=option_value, label=option_label
                            )
                        )
                except Exception as e:
                    _LOGGER.error(
                        f"Error fetching directions for route {route_id}: {str(e)}"
                    )

            if not route_direction_options:
                errors["base"] = "no_matching_routes"
                return self.async_show_form(step_id="route", errors=errors)

            return self.async_show_form(
                step_id="route",
                data_schema=vol.Schema(
                    {
                        vol.Required("route_direction"): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=route_direction_options,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                                custom_value=False,
                            )
                        ),
                    }
                ),
                errors=errors,
            )

        except Exception as e:
            _LOGGER.error(f"Error fetching stop details: {str(e)}")
            errors["base"] = "cannot_fetch_stop_details"
            return self.async_show_form(step_id="route", errors=errors)

    async def async_step_select_station_for_route(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle station selection for the chosen route."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            station_id = user_input["station"]
            self.data[CONF_STOP] = self.route_stations[station_id]
            self.data[CONF_STOP_ID] = station_id
            return await self.async_step_route()

        try:
            route_id = int(self.data[CONF_ROUTE_ID])
            route_type = int(self.data[CONF_ROUTE_TYPE])
            stops_request = StopRequest(route_id=route_id, route_type=route_type)
            stops = await self.ptv_api.stops_api.get_stops_for_route(stops_request)

            if not stops or "stops" not in stops:
                errors["base"] = "no_stations_found"
                return self.async_show_form(
                    step_id="select_station_for_route",
                    errors=errors,
                )

            self.route_stations = {
                str(stop["stop_id"]): {
                    "name": stop["stop_name"],
                    "suburb": stop.get("stop_suburb", ""),
                    "latitude": stop["stop_latitude"],
                    "longitude": stop["stop_longitude"],
                }
                for stop in stops["stops"]
            }

            station_options = [
                selector.SelectOptionDict(
                    value=stop_id, label=f"{details['name']} ({details['suburb']})"
                )
                for stop_id, details in sorted(
                    self.route_stations.items(), key=lambda x: x[1]["name"]
                )
            ]

            return self.async_show_form(
                step_id="select_station_for_route",
                data_schema=vol.Schema(
                    {
                        vol.Required("station"): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=station_options,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                                custom_value=False,
                            )
                        ),
                    }
                ),
                errors=errors,
            )

        except Exception as e:
            _LOGGER.error(f"Error fetching stations for route: {str(e)}")
            errors["base"] = "cannot_fetch_stations"
            return self.async_show_form(
                step_id="select_station_for_route",
                errors=errors,
            )

    async def async_step_final_config(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle final configuration and create the config entry."""
        errors: Dict[str, str] = {}
        _LOGGER.debug(f"IN FINAL CONFIG - Data: {self.data}")

        if user_input is not None:
            try:
                # Create the config entry
                title = f"PTV - {self.data[CONF_STOP]['name']} - {self.data[CONF_DIRECTION_ID]}"
                _LOGGER.debug(
                    f"Creating entry with title: {title} and data: {self.data}"
                )
                return self.async_create_entry(title=title, data=self.data)
            except Exception as e:
                _LOGGER.error(f"Error creating config entry: {str(e)}")
                errors["base"] = "unknown"

        # Show a confirmation form
        return self.async_show_form(
            step_id="final_config",
            data_schema=vol.Schema(
                {
                    vol.Required("confirm", default=True): bool,
                }
            ),
            description_placeholders={
                "stop_name": self.data[CONF_STOP]["name"],
                "route_name": self.data[CONF_ROUTE_NAME],
                "direction_name": self.data[CONF_DIRECTION_ID],
            },
            errors=errors,
        )
