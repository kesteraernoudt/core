"""Support for dobiss switchs."""
from datetime import timedelta

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_PLATFORM
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN

import logging

from dobissapi import (
    DobissAPI,
    DobissSwitch,
    ICON_FROM_DOBISS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up dobissswitch."""

    dobiss = hass.data[DOMAIN][config_entry.entry_id]
    # _LOGGER.warn("set up dobiss switch on {}".format(dobiss.url))

    d_entities = dobiss.get_devices_by_type(DobissSwitch)
    entities = []
    for d in d_entities:
        # _LOGGER.warn("set up dobiss switch on {}".format(dobiss.url))
        entities.append(HADobissSwitch(d))
    if entities:
        async_add_entities(entities)


class HADobissSwitch(SwitchEntity):
    """Dobiss switch device."""

    should_poll = False

    def __init__(self, dobissswitch: DobissSwitch):
        """Init dobiss Switch device."""
        super().__init__()
        self._dobissswitch = dobissswitch

    @property
    def icon(self):
        """Return the icon to use in the frontend"""
        return ICON_FROM_DOBISS[self._dobissswitch.icons_id]

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        self._dobissswitch.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        self._dobissswitch.remove_callback(self.async_write_ha_state)

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._dobissswitch.is_on

    async def async_turn_on(self, **kwargs):
        """Turn on or control the switch."""
        await self._dobissswitch.turn_on(**kwargs)

    async def async_turn_off(self, **kwargs):
        """Instruct the switch to turn off."""
        await self._dobissswitch.turn_off()

    @property
    def name(self):
        """Return the display name of this switch."""
        return self._dobissswitch.name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._dobissswitch.object_id