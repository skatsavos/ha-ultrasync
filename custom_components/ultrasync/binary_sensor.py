"""Monitor UltraSync zones as binary sensors."""

import logging
from typing import Callable, List

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    DATA_COORDINATOR,
    DOMAIN,
    SENSOR_UPDATE_LISTENER,
)
from .entity import UltraSyncEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: Callable[[List[BinarySensorEntity], bool], None],
) -> None:
    """Set up UltraSync binary sensors."""

    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    binary_sensors = {}

    @callback
    def _auto_manage_sensors(
        areas: dict,
        zones: dict,
        outputs: dict,
        history_data: dict,
    ) -> None:
        """Create binary sensors for detected UltraSync zones."""

        new_entities = []
        detected = set()

        for meta in zones:
            bank_no = meta["bank"]
            zone_number = bank_no + 1
            zone_id = f"zone{zone_number:02d}"

            detected.add(zone_id)

            if zone_id not in binary_sensors:
                # Get the configured device class for this zone.
                # Default to "door" if no setting exists yet.
                device_class = entry.options.get(
                    f"zone_device_class_{zone_number}",
                    "door",
                )

                binary_sensors[zone_id] = UltraSyncZone(
                    coordinator=coordinator,
                    entry_id=entry.entry_id,
                    entry_name=entry.data[CONF_NAME],
                    zone_id=zone_id,
                    zone_name=meta.get(
                        "name",
                        f"Zone {zone_number}",
                    ),
                    device_class=device_class,
                )

                new_entities.append(binary_sensors[zone_id])

                _LOGGER.debug(
                    "Detected %s.%s with device class %s",
                    entry.data[CONF_NAME],
                    zone_id,
                    device_class,
                )

            binary_sensors[zone_id].set_metadata(meta)

        if new_entities:
            async_add_entities(new_entities)

        # Remove zones which are no longer reported by the panel.
        for zone_id in set(binary_sensors) - detected:
            entity = binary_sensors.pop(zone_id)
            entry.async_create_task(hass, entity.async_remove())


    hass.data[DOMAIN][entry.entry_id][
        "binary_sensor_update_listener"
    ] = async_dispatcher_connect(
        hass,
        SENSOR_UPDATE_LISTENER,
        _auto_manage_sensors,
    )


class UltraSyncZone(UltraSyncEntity, BinarySensorEntity):
    """Representation of an UltraSync zone."""

    _attr_should_poll = False

    def __init__(
        self,
        coordinator,
        entry_id,
        entry_name,
        zone_id,
        zone_name,
        device_class,
    ):
        """Initialize an UltraSync zone."""

        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            name=f"{entry_name} {zone_name}",
        )

        self._zone_id = zone_id
        self._unique_id = f"{entry_id}_{zone_id}"
        self._attributes = {}

        self._attr_device_class = device_class

    @property
    def unique_id(self):
        """Return the unique ID."""

        return self._unique_id

    @property
    def extra_state_attributes(self):
        """Return additional zone information."""

        return self._attributes

    @property
    def is_on(self):
        """Return True when the zone is not Ready."""

        value = self.coordinator.data.get(
            f"{self._zone_id}_state"
        )

        if value is None:
            return None

        return value != "Ready"

    def set_metadata(self, metadata):
        """Update zone metadata."""

        self._attributes.update(metadata)
