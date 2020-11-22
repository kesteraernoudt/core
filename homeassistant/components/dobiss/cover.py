"""Support for dobiss covers."""
from datetime import timedelta

from homeassistant.const import CONF_PLATFORM
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from homeassistant.components.cover import (
    DEVICE_CLASS_SHADE,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_STOP,
    CoverEntity,
)

from .const import DOMAIN

import logging

from dobissapi import (
    DobissAPI,
    DobissSwitch,
    DOBISS_UP,
    DOBISS_DOWN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up dobissswitch."""

    dobiss = hass.data[DOMAIN][config_entry.entry_id]
    # _LOGGER.warn(f"set up dobiss switch on {dobiss.host}")

    d_entities = dobiss.get_devices_by_type(DobissSwitch)
    entities = []
    for d in d_entities:
        if d.buddy:
            # only add the up cover, and his buddy is down
            if d.icons_id == DOBISS_UP:
                # _LOGGER.warn(f"set up dobiss cover {d.name} and {d.buddy.name}")
                entities.append(HADobissCover(d, d.buddy))
    if entities:
        async_add_entities(entities)


class HADobissCover(CoverEntity):
    """Dobiss Cover device."""

    should_poll = False

    supported_features = SUPPORT_STOP | SUPPORT_OPEN | SUPPORT_CLOSE

    decice_class = DEVICE_CLASS_SHADE

    def __init__(self, up: DobissSwitch, down: DobissSwitch):
        """Init dobiss Switch device."""
        super().__init__()
        self._up = up
        self._down = down

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        self._up.register_callback(self.async_write_ha_state)
        self._down.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        self._up.remove_callback(self.async_write_ha_state)
        self._down.remove_callback(self.async_write_ha_state)

    @property
    def name(self):
        """Return the display name of this cover."""
        return self._up.name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._up.object_id}-{self._down.object_id}"

    @property
    def available(self) -> bool:
        """Return True."""
        return True

    @property
    def is_closed(self):
        """ Unknown """
        return None

    @property
    def is_closing(self):
        """Return if the cover is closing or not."""
        return self._down.value > 0 if self._down.value else None

    @property
    def is_opening(self):
        """Return if the cover is opening or not."""
        return self._up.value > 0 if self._up.value else None

    # These methods allow HA to tell the actual device what to do. In this case, move
    # the cover to the desired position, or open and close it all the way.
    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        await self._up.turn_on()

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        await self._down.turn_on()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        await self._up.turn_off()
        await self._down.turn_off()
