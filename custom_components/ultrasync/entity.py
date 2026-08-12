"""Defines the base UltraSync entity."""

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class UltraSyncEntity(CoordinatorEntity):
    """Base class for a UltraSync entity."""

    def __init__(
        self,
        *,
        coordinator,
        entry_id: str,
        name: str,
    ) -> None:
        """Initialize the UltraSync entity."""

        super().__init__(coordinator)

        self._entry_id = entry_id
        self._attr_name = name

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="UltraSync",
            manufacturer="Interlogix",
        )
