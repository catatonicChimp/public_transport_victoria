"""Config flow for Public Transport Victoria integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .PublicTransportVictoria.public_transport_victoria import PTVApi
from .PublicTransportVictoria.api.routes import RouteRequest, RoutesAPI

from .const import DOMAIN, CONF_DEV_ID, CONF_API_KEY, CONF_ROUTE_TYPE, CONF_STOP_ID, CONF_ROUTE_ID, CONF_DIRECTION_ID

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

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                self.ptv_api = PTVApi(self.hass, user_input[CONF_DEV_ID], user_input[CONF_API_KEY])
                # Test the API connection using a simple API call
                # For example, let's try to get route types
                route_types = await self.ptv_api.get_route_types()
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
            data_schema=vol.Schema({
                vol.Required(CONF_DEV_ID): str,
                vol.Required(CONF_API_KEY): str,
            }),
            errors=errors,
        )

    async def async_step_route_type(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle route type selection."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_stop()

        route_types = await self.ptv_api.route_types_api.get_route_types()
        route_type_options = {str(rt['route_type']): rt['route_type_name'] for rt in route_types['route_types']}

        return self.async_show_form(
            step_id="route_type",
            data_schema=vol.Schema({
                vol.Required(CONF_ROUTE_TYPE): vol.In(route_type_options),
            }),
            errors=errors,
        )

    async def async_step_stop(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle stop selection."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_route()

        # Here you would typically fetch stops based on the selected route type
        # For simplicity, we're just asking for a stop ID directly
        return self.async_show_form(
            step_id="stop",
            data_schema=vol.Schema({
                vol.Required(CONF_STOP_ID): int,
            }),
            errors=errors,
        )

    async def async_step_route(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle route selection."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_direction()
        routes_api = RoutesAPI(self.ptv_api.client)
        request = RouteRequest(
            route_types=[self.data[CONF_ROUTE_TYPE]]
        )
        routes = await routes_api.get_all_routes(request)
        route_options = {str(r['route_id']): r['route_name'] for r in routes['routes']}

        return self.async_show_form(
            step_id="route",
            data_schema=vol.Schema({
                vol.Required(CONF_ROUTE_ID): vol.In(route_options),
            }),
            errors=errors,
        )

    async def async_step_direction(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle direction selection."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            self.data.update(user_input)
            return self.async_create_entry(title="Public Transport Victoria", data=self.data)

        directions = await self.ptv_api.directions_api.get_directions_for_route(
            self.data[CONF_ROUTE_ID]
        )
        direction_options = {str(d['direction_id']): d['direction_name'] for d in directions['directions']}

        return self.async_show_form(
            step_id="direction",
            data_schema=vol.Schema({
                vol.Required(CONF_DIRECTION_ID): vol.In(direction_options),
            }),
            errors=errors,
        )
