"""Config flow for the Interlogix/Hills ComNav UltraSync Hub."""

from __future__ import annotations

import logging
from typing import Any

import ultrasync
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    DATA_COORDINATOR,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class AuthFailureException(Exception):
    """Raised when authentication with the UltraSync hub fails."""


def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate that the user input allows us to connect."""
    usync = ultrasync.UltraSync(
        host=data[CONF_HOST],
        user=data[CONF_USERNAME],
        pin=data[CONF_PIN],
    )

    # Validate by attempting to authenticate with the host.
    if not usync.login():
        raise AuthFailureException()


class UltraSyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the UltraSync configuration flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return UltraSyncOptionsFlowHandler(config_entry)

    def _get_user_schema(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Return the configuration form schema."""
        user_input = user_input or {}

        return vol.Schema(
            {
                vol.Optional(
                    CONF_NAME,
                    default=user_input.get(CONF_NAME, DEFAULT_NAME),
                ): str,
                vol.Required(
                    CONF_HOST,
                    default=user_input.get(CONF_HOST, ""),
                ): str,
                vol.Required(
                    CONF_USERNAME,
                    default=user_input.get(CONF_USERNAME, ""),
                ): str,
                vol.Required(
                    CONF_PIN,
                    default=user_input.get(CONF_PIN, ""),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD
                    )
                ),
            }
        )

    @staticmethod
    def _validate_pin(pin: Any) -> str | None:
        """Validate the UltraSync PIN."""
        if pin is None:
            return "invalid_pin"

        pin = str(pin)

        if not pin.isdigit():
            return "invalid_pin"

        if not 4 <= len(pin) <= 8:
            return "invalid_pin_length"

        return None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle the initial configuration step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}

        if user_input is not None:
            pin_error = self._validate_pin(user_input.get(CONF_PIN))

            if pin_error:
                errors["pin"] = pin_error
            else:
                try:
                    await self.hass.async_add_executor_job(
                        validate_input,
                        self.hass,
                        user_input,
                    )
                except AuthFailureException:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception(
                        "Unexpected exception while connecting to UltraSync hub"
                    )
                    errors["base"] = "unknown"
                else:
                    return self.async_create_entry(
                        title=user_input.get(CONF_NAME, user_input[CONF_HOST]),
                        data=user_input,
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_user_schema(user_input),
            errors=errors,
        )


class UltraSyncOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle UltraSync client options."""

    def __init__(
        self,
        config_entry: config_entries.ConfigEntry,
    ) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    def _get_current_data(self) -> dict[str, Any]:
        """Return the current configuration and options."""
        return {
            **self._config_entry.data,
            **self._config_entry.options,
        }

    def _get_options_schema(
        self,
        current_data: dict[str, Any],
        user_input: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the options form schema."""
        user_input = user_input or {}

        options: dict[Any, Any] = {
            vol.Required(
                CONF_HOST,
                default=user_input.get(
                    CONF_HOST,
                    current_data.get(CONF_HOST, ""),
                ),
            ): str,
            vol.Required(
                CONF_USERNAME,
                default=user_input.get(
                    CONF_USERNAME,
                    current_data.get(CONF_USERNAME, ""),
                ),
            ): str,
            vol.Required(
                CONF_PIN,
                default=user_input.get(
                    CONF_PIN,
                    current_data.get(CONF_PIN, ""),
                ),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.PASSWORD
                )
            ),
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=user_input.get(
                    CONF_SCAN_INTERVAL,
                    current_data.get(
                        CONF_SCAN_INTERVAL,
                        DEFAULT_SCAN_INTERVAL,
                    ),
                ),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=1),
            ),
        }

        coordinator_data = self.hass.data.get(DOMAIN, {}).get(
            self._config_entry.entry_id,
            {},
        )

        coordinator = coordinator_data.get(DATA_COORDINATOR)

        if coordinator is not None:
            for zone in coordinator.zones:
                bank_no = zone.get("bank", 0)
                zone_number = bank_no + 1

                zone_name = zone.get(
                    "name",
                    f"Zone {zone_number}",
                )

                option_name = f"zone_device_class_{zone_number}"

                current_device_class = user_input.get(
                    option_name,
                    self._config_entry.options.get(
                        option_name,
                        "door",
                    ),
                )

                options[
                    vol.Required(
                        option_name,
                        default=current_device_class,
                    )
                ] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value="door",
                                label=f"{zone_name} - Door",
                            ),
                            selector.SelectOptionDict(
                                value="motion",
                                label=f"{zone_name} - Motion",
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )

        return vol.Schema(options)

    @staticmethod
    def _validate_pin(pin: Any) -> str | None:
        """Validate the UltraSync PIN."""
        if not pin:
            return None

        pin = str(pin)

        if not pin.isdigit():
            return "invalid_pin"

        if not 4 <= len(pin) <= 8:
            return "invalid_pin_length"

        return None

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Manage UltraSync options."""
        current_data = self._get_current_data()
        errors: dict[str, str] = {}

        if user_input is not None:
            pin_error = self._validate_pin(user_input.get(CONF_PIN))

            if pin_error:
                errors["pin"] = pin_error
            else:
                return self.async_create_entry(
                    title="",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_options_schema(
                current_data,
                user_input,
            ),
            errors=errors,
        )
