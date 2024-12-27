"""Config flow for Public Transport Victoria integration."""

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
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
    CONF_STOP_NAME,
    CONF_ROUTE_ID,
    CONF_ROUTE_NAME,
    CONF_DIRECTION_ID,
    CONF_DIRECTION_NAME,
    CONF_ROUTE_TYPE_NAME,
)

_LOGGER = logging.getLogger(__name__)

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class PTVConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Public Transport Victoria."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.ptv_api: Optional[PTVApi] = None
        self.data: Dict[str, Any] = {}

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle the initial step."""
        _LOGGER.debug("Initialized self.data: %s", self.data)

        # Check if there is already a config entry for this integration
        existing_entries = self._async_current_entries()
        if existing_entries:
            _LOGGER.debug("Existing entry found, using existing credentials.")
            entry = existing_entries[0]
            _LOGGER.debug("Existing entry data: %s", entry.data)

            # Copy dev_id and api_key to self.data so it persists across steps
            self.data[CONF_DEV_ID] = entry.data[CONF_DEV_ID]
            self.data[CONF_API_KEY] = entry.data[CONF_API_KEY]
            _LOGGER.debug("Carried over API key and ID into self.data: %s", self.data)

            self.ptv_api = PTVApi(
                self.hass, entry.data[CONF_DEV_ID], entry.data[CONF_API_KEY]
            )
            route_types = await self.ptv_api.route_types_api.get_route_types()
            return await self.async_step_route_type()

        # If no existing entry, prompt user for API key and ID
        data_schema = vol.Schema(
            {
                vol.Required(CONF_DEV_ID): str,
                vol.Required(CONF_API_KEY): str,
            }
        )

        errors = {}
        if user_input is not None:
            try:
                _LOGGER.debug("Received user input: %s", user_input)
                # Initialize PTVApi to validate API key and fetch route types
                self.ptv_api = PTVApi(
                    self.hass, user_input[CONF_DEV_ID], user_input[CONF_API_KEY]
                )
                route_types = await self.ptv_api.route_types_api.get_route_types()

                if not route_types:
                    raise CannotConnect

                # Store the API key and ID in self.data for use in subsequent steps
                self.data[CONF_DEV_ID] = user_input[CONF_DEV_ID]
                self.data[CONF_API_KEY] = user_input[CONF_API_KEY]
                _LOGGER.debug("Stored API key and ID in self.data: %s", self.data)

                return await self.async_step_route_type()

            except CannotConnect:
                _LOGGER.error("Cannot connect to Public Transport Victoria API.")
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Show the form to input the API ID and Key
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_route_type(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle route type selection."""
        if user_input is not None:
            self.data[CONF_ROUTE_TYPE] = int(user_input[CONF_ROUTE_TYPE])
            return await self.async_step_search_method()

        route_types = await self.ptv_api.route_types_api.get_route_types()
        route_type_options = [
            selector.SelectOptionDict(
                value=str(rt["route_type"]),
                label=rt["route_type_name"]
            )
            for rt in route_types["route_types"]
        ]

        return self.async_show_form(
            step_id="route_type",
            data_schema=vol.Schema({
                vol.Required(CONF_ROUTE_TYPE): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=route_type_options)
                ),
            }),
            description_placeholders={
                "route_types": ", ".join(rt["route_type_name"] for rt in route_types["route_types"])
            }
        )

    async def async_step_search_method(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle search method selection."""
        if user_input is not None:
            search_method = user_input["search_method"]
            return await getattr(self, f"async_step_{search_method}")()

        return self.async_show_menu(
            step_id="search_method",
            menu_options=["line_name", "stop_name", "suburb", "map"],
        )

    async def async_step_line_name(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle search by line name."""
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_select_station_for_route()

        routes = await self.ptv_api.routes_api.get_all_routes(
            RouteRequest(route_types=[int(self.data[CONF_ROUTE_TYPE])])
        )
        route_options = {
            str(route["route_id"]): f"{route.get('route_number', '')} - {route['route_name']}"
            for route in routes["routes"]
        }

        return self.async_show_form(
            step_id="line_name",
            data_schema=vol.Schema({
                vol.Required(CONF_ROUTE_ID): vol.In(route_options),
            }),
        )

    # ... (implement other steps like async_step_stop_name, async_step_suburb, async_step_map)

    async def async_step_select_station_for_route(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle station selection for the chosen route."""
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_direction()

        stops = await self.ptv_api.stops_api.get_stops_for_route(
            StopRequest(route_id=int(self.data[CONF_ROUTE_ID]), route_type=int(self.data[CONF_ROUTE_TYPE]))
        )
        station_options = [
            selector.SelectOptionDict(value=str(stop["stop_id"]), label=f"{stop['stop_name']} ({stop.get('stop_suburb', '')})")
            for stop in stops["stops"]
        ]

        return self.async_show_form(
            step_id="select_station_for_route",
            data_schema=vol.Schema({
                vol.Required(CONF_STOP_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=station_options)
                ),
            }),
        )

    async def async_step_direction(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle direction selection."""
        if user_input is not None:
            self.data.update(user_input)
            return self.async_create_entry(
                title=f"PTV - {self.data[CONF_STOP_NAME]['name']} - {self.data[CONF_DIRECTION_NAME]}",
                data=self.data
            )

        directions = await self.ptv_api.directions_api.get_directions_for_route(
            DirectionRequest(route_id=int(self.data[CONF_ROUTE_ID]))
        )
        direction_options = {
            str(direction["direction_id"]): direction["direction_name"]
            for direction in directions["directions"]
        }

        return self.async_show_form(
            step_id="direction",
            data_schema=vol.Schema({
                vol.Required(CONF_DIRECTION_ID): vol.In(direction_options),
            }),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return PTVOptionsFlow(config_entry)

class PTVOptionsFlow(config_entries.OptionsFlow):
    """Handle PTV options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("update_interval", default=self.config_entry.options.get("update_interval", 60)): int,
            })
        )
