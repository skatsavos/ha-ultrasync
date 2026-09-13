"""Monitor UltraSync zones as binary sensors."""

from __future__ import annotations

import logging
from collections.abc import Callable

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
    async_add_entities: Callable,
) -> None:
    """Set up UltraSync binary sensors."""

    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    binary_sensors: dict[str, UltraSyncZone] = {}

    @callback
    def _auto_manage_sensors(
        areas: list,
        zones: list,
        outputs: list,
        history_data: list,
    ) -> None:
        """Create and manage binary sensors for detected UltraSync zones."""

        new_entities: list[UltraSyncZone] = []
        detected: set[str] = set()

        entry_name = entry.data.get(
            CONF_NAME,
            entry.data.get("name", "UltraSync"),
        )

        for meta in zones:
            bank_no = meta.get("bank")

            if bank_no is None:
                _LOGGER.warning(
                    "Ignoring UltraSync zone without a bank number: %s",
                    meta,
                )
                continue

            zone_number = bank_no + 1
            zone_id = f"zone{zone_number:02d}"

            detected.add(zone_id)

            if zone_id not in binary_sensors:
                device_class = entry.options.get(
                    f"zone_device_class_{zone_number}",
                    "door",
                )

                zone_name = meta.get(
                    "name",
                    f"Zone {zone_number}",
                )

                entity = UltraSyncZone(
                    coordinator=coordinator,
                    entry=entry,
                    entry_name=entry_name,
                    zone_id=zone_id,
                    zone_name=zone_name,
                    device_class=device_class,
                )

                binary_sensors[zone_id] = entity
                new_entities.append(entity)

                _LOGGER.debug(
                    "Detected %s.%s with device class %s",
                    entry_name,
                    zone_id,
                    device_class,
                )

            binary_sensors[zone_id].set_metadata(meta)

        if new_entities:
            async_add_entities(new_entities)

        # Remove zones that are no longer reported by the panel.
        removed_zone_ids = set(binary_sensors) - detected

        for zone_id in removed_zone_ids:
            entity = binary_sensors.pop(zone_id)

            entry.async_create_task(
                hass,
                entity.async_remove(),
            )

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
        entry: ConfigEntry,
        entry_name: str,
        zone_id: str,
        zone_name: str,
        device_class: str,
    ) -> None:
        """Initialize an UltraSync zone."""

        super().__init__(
            coordinator=coordinator,
            entry=entry,
        )

        self._zone_id = zone_id
        self._unique_id = f"{entry.entry_id}_{zone_id}"
        self._attributes: dict = {}

        self._attr_name = f"{entry_name} {zone_name}"
        self._attr_device_class = device_class

    @property
    def unique_id(self) -> str:
        """Return the unique ID."""
        return self._unique_id

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional zone information."""
        return self._attributes

    @property
    def is_on(self) -> bool | None:
        """Return True when the zone is not Ready."""

        value = self.coordinator.data.get(
            f"{self._zone_id}_state"
        )

        if value is None:
            return None

        return value != "Ready"

    def set_metadata(self, metadata: dict) -> None:
        """Update zone metadata."""
        self._attributes.update(metadata)
