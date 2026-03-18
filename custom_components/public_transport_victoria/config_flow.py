"""Config flow for Public Transport Victoria integration."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_ID

from .const import (
    CONF_DIRECTION,
    CONF_DIRECTION_NAME,
    CONF_ROUTE,
    CONF_ROUTE_NAME,
    CONF_ROUTE_TYPE,
    CONF_ROUTE_TYPE_NAME,
    CONF_STOP,
    CONF_STOP_NAME,
    DOMAIN
)
from .PublicTransportVictoria.public_transport_victoria import (
    CannotConnect,
    Connector,
    InvalidAuth,
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Public Transport Victoria."""

    VERSION = 1

    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if not hasattr(self, "data"):
            self.data = {}

        existing_entries = self._async_current_entries()
        if existing_entries:
            entry = existing_entries[0]
            self.data[CONF_ID] = entry.data[CONF_ID]
            self.data[CONF_API_KEY] = entry.data[CONF_API_KEY]
            self.connector = Connector(
                self.hass, entry.data[CONF_ID], entry.data[CONF_API_KEY]
            )
            self.route_types = await self.connector.async_route_types()
            return await self.async_step_route_types()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ID): str,
                vol.Required(CONF_API_KEY): str,
            }
        )

        errors = {}
        if user_input is not None:
            try:
                self.connector = Connector(
                    self.hass, user_input[CONF_ID], user_input[CONF_API_KEY]
                )
                self.route_types = await self.connector.async_route_types()
                self.data[CONF_ID] = user_input[CONF_ID]
                self.data[CONF_API_KEY] = user_input[CONF_API_KEY]
                return await self.async_step_route_types()

            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_route_types(self, user_input=None):
        """Handle the route types step."""
        data_schema = vol.Schema({
            vol.Required(CONF_ROUTE_TYPE, default=next(iter(self.route_types))): vol.In(self.route_types),
        })

        errors = {}
        if user_input is not None:
            try:
                self.routes = await self.connector.async_routes(
                    user_input[CONF_ROUTE_TYPE]
                )
                self.data[CONF_ROUTE_TYPE] = user_input[CONF_ROUTE_TYPE]
                self.data[CONF_ROUTE_TYPE_NAME] = self.route_types[user_input[CONF_ROUTE_TYPE]]
                return await self.async_step_routes()

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="route_types", data_schema=data_schema, errors=errors
        )

    async def async_step_routes(self, user_input=None):
        """Handle the route selection step."""
        data_schema = vol.Schema({
            vol.Required(CONF_ROUTE, default=next(iter(self.routes))): vol.In(self.routes),
        })

        errors = {}
        if user_input is not None:
            try:
                self.data[CONF_ROUTE] = user_input[CONF_ROUTE]
                self.data[CONF_ROUTE_NAME] = self.routes[user_input[CONF_ROUTE]]

                # Fetch all stops on the route (no direction filter — users pick
                # their stop and see departures in all directions as attributes)
                self.stops = await self.connector.async_stops(user_input[CONF_ROUTE])

                return await self.async_step_stops()

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="routes", data_schema=data_schema, errors=errors
        )

    async def async_step_stops(self, user_input=None):
        """Handle the stop selection step."""
        data_schema = vol.Schema({
            vol.Required(CONF_STOP, default=next(iter(self.stops))): vol.In(self.stops),
        })

        errors = {}
        if user_input is not None:
            try:
                self.data[CONF_STOP] = user_input[CONF_STOP]
                self.data[CONF_STOP_NAME] = self.stops[user_input[CONF_STOP]]

                # No direction filter — direction is shown as an attribute on each
                # departure entity so users see where each service is headed
                self.data[CONF_DIRECTION] = None
                self.data[CONF_DIRECTION_NAME] = ""

                title = "{} from {}".format(
                    self.data[CONF_ROUTE_NAME],
                    self.data[CONF_STOP_NAME],
                )
                return self.async_create_entry(title=title, data=self.data)

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="stops", data_schema=data_schema, errors=errors
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Public Transport Victoria."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry
        self.data = dict(config_entry.data)
        self.connector = None
        self.stops = {}

    async def async_step_init(self, user_input=None):
        """Start the options flow by re-fetching stops for the current route."""
        self.connector = Connector(
            self.hass,
            self.data[CONF_ID],
            self.data[CONF_API_KEY],
        )
        self.connector.route_type = self.data[CONF_ROUTE_TYPE]
        self.stops = await self.connector.async_stops(self.data[CONF_ROUTE])
        return await self.async_step_stop()

    async def async_step_stop(self, user_input=None):
        """Let the user pick a new stop."""
        current_stop = self.data[CONF_STOP]
        data_schema = vol.Schema({
            vol.Required(
                CONF_STOP,
                default=current_stop if current_stop in self.stops else next(iter(self.stops)),
            ): vol.In(self.stops),
        })

        errors = {}
        if user_input is not None:
            try:
                self.data[CONF_STOP] = user_input[CONF_STOP]
                self.data[CONF_STOP_NAME] = self.stops[user_input[CONF_STOP]]
                self.data[CONF_DIRECTION] = None
                self.data[CONF_DIRECTION_NAME] = ""
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=self.data
                )
                return self.async_create_entry(title="", data={})
            except Exception:
                _LOGGER.exception("Unexpected exception in options stop step")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="stop", data_schema=data_schema, errors=errors
        )
