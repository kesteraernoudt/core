"""Support for dobiss climate control."""
from datetime import timedelta

from homeassistant.helpers.entity import Entity
from homeassistant.const import (
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_ILLUMINANCE,
    TEMP_CELSIUS,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.components.climate.const import (
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_DRY,
    CURRENT_HVAC_FAN,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    HVAC_MODE_AUTO,
    HVAC_MODE_OFF,
)
from homeassistant.components.climate import (
    ClimateEntity,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    HVAC_MODE_HEAT,
)

from .const import DOMAIN, KEY_API

import logging

from dobissapi import (
    DobissAPI,
    DobissTempSensor,
    ICON_FROM_DOBISS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up dobisssensor."""

    dobiss = hass.data[DOMAIN][config_entry.entry_id][KEY_API].api

    # only add HVAC objects for temperature sensors when there is at least a schedule entry
    if len(dobiss.calendars) == 0:
        return

    entities = []
    d_entities = dobiss.get_devices_by_type(DobissTempSensor)
    for d in d_entities:
        entities.append(HADobissClimateControl(d))
    if entities:
        async_add_entities(entities)


class HADobissClimateControl(ClimateEntity):
    """Dobiss ssensor device."""

    should_poll = False

    temperature_unit = TEMP_CELSIUS

    supported_features = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

    def __init__(self, dobisssensor: DobissTempSensor):
        """Init dobiss ClimateControl device."""
        super().__init__()
        self._dobisssensor = dobisssensor

    @property
    def device_info(self):
        """Information about this entity/device."""
        return {
            "identifiers": {(DOMAIN, f"climatecontrol_{self._dobisssensor.object_id}")},
            "name": f"climatecontrol_{self.name}",
            "manufacturer": "dobiss",
        }

    @property
    def device_state_attributes(self):
        """Return supported attributes."""
        return self._dobisssensor.attributes

    @property
    def available(self) -> bool:
        """Return True."""
        return True

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        self._dobisssensor.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        self._dobisssensor.remove_callback(self.async_write_ha_state)

    @property
    def name(self):
        """Return the display name of this sensor."""
        return self._dobisssensor.name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"climatecontrol_{self._dobisssensor.object_id}"

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._dobisssensor.value

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._dobisssensor.asked

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 0.5

    async def async_set_temperature(self, **kwargs):
        await self._dobisssensor.set_temperature(**kwargs)

    async def async_set_hvac_mode(self, hvac_mode: str):
        await self._dobisssensor.set_hvac_mode(hvac_mode)

    async def async_set_preset_mode(self, preset_mode: str):
        await self._dobisssensor.set_preset_mode(preset_mode)

    @property
    def preset_modes(self):
        return self._dobisssensor._dobiss.calendars

    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp.
        Requires SUPPORT_PRESET_MODE.
        """
        return self._dobisssensor.calendar

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.
        Need to be one of HVAC_MODE_*.
        """
        if self._dobisssensor.time == None:
            return HVAC_MODE_OFF
        if self._dobisssensor.time >= 0:
            return HVAC_MODE_HEAT
        return HVAC_MODE_AUTO

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        modes = []
        modes.append(HVAC_MODE_HEAT)
        modes.append(HVAC_MODE_AUTO)
        modes.append(HVAC_MODE_OFF)
        return modes

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported.

        Need to be one of CURRENT_HVAC_*.
        """
        if self._dobisssensor.status == 1:
            return CURRENT_HVAC_HEAT
        return CURRENT_HVAC_IDLE
