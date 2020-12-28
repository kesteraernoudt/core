"""The dobiss integration."""
import asyncio

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import *  # pylint:disable=unused-import

import logging

from dobissapi import DobissAPI
import requests

_LOGGER = logging.getLogger(__name__)
# _LOGGER.setLevel(logging.DEBUG)

PLATFORMS = ["light", "switch", "sensor", "cover", "binary_sensor"]
# PLATFORMS = ["light"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the dobiss component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up dobiss from a config entry."""

    client = HADobiss(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client
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
            self.hass.data[DOMAIN][self.config_entry.entry_id] = self.api

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
        dobiss = hass.data[DOMAIN][entry.entry_id]
        await dobiss.update_all(force=True)
