"""The dobiss integration."""
import asyncio

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

import logging

from dobissapi import DobissAPI, logger
import requests

# logger.setLevel(logging.DEBUG)

PLATFORMS = ["light", "switch", "sensor", "cover"]
# PLATFORMS = ["light"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the dobiss component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up dobiss from a config entry."""

    dobiss = DobissAPI(entry.data["secret"], entry.data["host"], entry.data["secure"])
    hass.data[DOMAIN][entry.entry_id] = dobiss

    logger.setLevel(logging.DEBUG)
    await dobiss.discovery()
    hass.async_create_task(dobiss.dobiss_monitor())

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
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
