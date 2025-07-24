"""Support for UltraSync alarm control panels."""
import logging
from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from ultrasync import AlarmScene
from functools import partial

from .const import (
    DATA_COORDINATOR,
    DATA_UNDO_UPDATE_LISTENER,
    DOMAIN,
    SENSOR_UPDATE_LISTENER,
    SENSORS,
)
from .coordinator import UltraSyncDataUpdateCoordinator
from .entity import UltraSyncEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the UltraSync alarm control panel."""
    coordinator: UltraSyncDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    _LOGGER.debug("Setting up UltraSync alarm control panel")

    entities = []
    for area in coordinator.areas:
        _LOGGER.debug("Found area: %s", area)
        entity = UltraSyncAlarmControlPanel(coordinator, entry, area)
        entities.append(entity)
        _LOGGER.debug("Created UltraSyncAlarmControlPanel: %s", entity.unique_id)

    async_add_entities(entities)
    _LOGGER.info("UltraSync alarm control panel setup completed with %d entities", len(entities))


class UltraSyncAlarmControlPanel(UltraSyncEntity, AlarmControlPanelEntity):
    """Representation of an UltraSync alarm control panel."""
    
    _attr_code_arm_required = False
    _attr_code_disarm_required = False

    def __init__(self, coordinator, entry, area):
        """Initialize the alarm control panel."""
        super().__init__(coordinator, entry)
        self._area = area
        self._bank = area["bank"]
        self._attr_name = area["name"]
        self._attr_unique_id = f"{entry.entry_id}_alarm_{self._bank}"

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        """Return the supported features."""
        return (
            AlarmControlPanelEntityFeature.ARM_HOME
            | AlarmControlPanelEntityFeature.ARM_AWAY
        )
        
    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the state of the alarm."""
        status = self._area.get("status", "").lower()

        if "ready" in status:
            return AlarmControlPanelState.DISARMED
        if "armed away" in status:
            return AlarmControlPanelState.ARMED_AWAY
        if "armed stay" in status:
            return AlarmControlPanelState.ARMED_HOME
        if "exit delay" in status or "arming" in status:
            return AlarmControlPanelState.ARMING
        if "alarm" in status:
            return AlarmControlPanelState.TRIGGERED

        _LOGGER.warning("Unknown alarm status for area %s: %s", self._area, status)
        return None

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        fn = partial(self.coordinator.hub.set_alarm, state=AlarmScene.DISARMED)
        await self.hass.async_add_executor_job(fn)
        await self.coordinator.async_request_refresh()
        
    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        fn = partial(self.coordinator.hub.set_alarm, state=AlarmScene.STAY)
        await self.hass.async_add_executor_job(fn)
        await self.coordinator.async_request_refresh()

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        fn = partial(self.coordinator.hub.set_alarm, state=AlarmScene.AWAY)
        await self.hass.async_add_executor_job(fn)
        await self.coordinator.async_request_refresh()

    async def async_update(self) -> None:
        """Update alarm panel state."""
        await self.coordinator.async_request_refresh()

