"""The dobiss integration."""
import asyncio

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import *  # pylint:disable=unused-import

import logging

from dobissapi import DobissAPI
import requests

_LOGGER = logging.getLogger(__name__)
# _LOGGER.setLevel(logging.DEBUG)

PLATFORMS = ["light", "switch", "sensor", "cover", "binary_sensor"]
# PLATFORMS = ["light"]

SERVICE_ACTION_REQUEST = "action_request"
SERVICE_STATUS_REQUEST = "status_request"
SERVICE_FORCE_UPDATE = "force_update"

ATTR_ADDRESS = "address"
ATTR_CHANNEL = "channel"
ATTR_ACTION = "action"
ATTR_OPTION1 = "option1"
ATTR_OPTION2 = "option2"


ACTION_REQUEST_SCHEMA = vol.Schema(
    vol.All(
        {
            vol.Required(ATTR_ADDRESS): vol.Coerce(int),
            vol.Required(ATTR_CHANNEL): vol.Coerce(int),
            vol.Required(ATTR_ACTION): vol.Coerce(int),
            vol.Optional(ATTR_OPTION1): vol.Any(int, float),
            vol.Optional(ATTR_OPTION2): vol.Any(int, float),
        }
    )
)
STATUS_REQUEST_SCHEMA = vol.Schema(
    vol.All(
        {
            vol.Optional(ATTR_ADDRESS): vol.Coerce(int),
            vol.Optional(ATTR_CHANNEL): vol.Coerce(int),
        }
    )
)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the dobiss component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up dobiss from a config entry."""

    client = HADobiss(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {KEY_API: client}

    if not await client.async_setup():
        return False

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    if hass.data[DOMAIN][entry.entry_id].unsub:
        hass.data[DOMAIN][entry.entry_id].unsub()
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class HADobiss:
    def __init__(self, hass, config_entry):
        """Initialize the Dobiss data."""
        self.hass = hass
        self.config_entry = config_entry
        self.api = None
        self.available = False
        self.unsub = None

    @property
    def host(self):
        """Return client host."""
        return self.config_entry.data[CONF_HOST]

    async def async_setup(self):
        """Set up the Dobiss client."""
        try:
            self.api = DobissAPI(
                self.config_entry.data["secret"],
                self.config_entry.data["host"],
                self.config_entry.data["secure"],
            )
            devices = self.api.get_all_devices()
            self.hass.data[DOMAIN][self.config_entry.entry_id][DEVICES] = devices

            # logger.setLevel(logging.DEBUG)
            await self.api.discovery()
            self.hass.async_create_task(self.api.dobiss_monitor())

            self.available = True
            _LOGGER.debug("Successfully connected to Dobiss")

        except:
            _LOGGER.exception("Can not connect to Dobiss")
            self.available = False
            raise

        self.add_options()
        self.unsub = self.config_entry.add_update_listener(self.update_listener)

        for component in PLATFORMS:
            self.hass.async_create_task(
                self.hass.config_entries.async_forward_entry_setup(
                    self.config_entry, component
                )
            )

        @callback
        async def handle_action_request(call):
            """Handle action_request service."""
            dobiss = self.api
            writedata = {
                "address": call.data.get("address"),
                "channel": call.data.get("channel"),
                "action": call.data.get("action"),
                "option1": call.data.get("option1"),
                "option2": call.data.get("option2"),
            }
            response = await dobiss.request(writedata)
            _LOGGER.info(await response.json())

        @callback
        async def handle_status_request(call):
            """Handle status_request service."""
            dobiss = self.api
            response = await dobiss.status(
                call.data.get(ATTR_ADDRESS), call.data.get(ATTR_CHANNEL)
            )
            _LOGGER.info(await response.json())

        @callback
        async def handle_force_update(call):
            """Handle status_request service."""
            dobiss = self.api
            await dobiss.update_all(force=True)

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_FORCE_UPDATE,
            handle_force_update,
        )
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_ACTION_REQUEST,
            handle_action_request,
            schema=ACTION_REQUEST_SCHEMA,
        )
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_STATUS_REQUEST,
            handle_status_request,
            schema=STATUS_REQUEST_SCHEMA,
        )

        return True

    def add_options(self):
        """Add options for Glances integration."""
        if not self.config_entry.options:
            options = {CONF_INVERT_BINARY_SENSOR: DEFAULT_INVERT_BINARY_SENSOR}
            self.hass.config_entries.async_update_entry(
                self.config_entry, options=options
            )

    @staticmethod
    async def update_listener(hass, entry):
        """Handle options update."""
        dobiss = hass.data[DOMAIN][entry.entry_id][KEY_API].api
        await dobiss.update_all(force=True)
