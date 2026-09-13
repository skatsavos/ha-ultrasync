"""Defines the base UltraSync entity."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class UltraSyncEntity(CoordinatorEntity):
    """Base class for an UltraSync entity."""

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)

        self.entry = entry

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="UltraSync",
            manufacturer="Interlogix",
        )
