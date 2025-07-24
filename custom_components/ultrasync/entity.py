"""Defines the base UltraSync entity."""
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


class UltraSyncEntity(CoordinatorEntity):
    """Base class for a UltraSync entity."""

    def __init__(self, coordinator, entry):
        """Initialize the entity."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="UltraSync",
            manufacturer="Interlogix",
        )
