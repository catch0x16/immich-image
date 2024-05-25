"""
Initialize Immich Image
"""
from datetime import timedelta
import logging
from typing import Final

from homeassistant.const import CONF_HOST

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.helpers.entity_component import EntityComponent

from custom_components.immich_image.views import ImmichImageView
from .const import DOMAIN
from .hub import ImmichHub, InvalidAuth
from .immich_image import ImmichImage

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL: Final = timedelta(seconds=30)

async def setup_view(hass: HomeAssistant, component: EntityComponent[ImmichImage]):
    _LOGGER.info("[setup_view] setting-up {DOMAIN}")
    hass.http.register_view(ImmichImageView(component))

# https://developers.home-assistant.io/docs/creating_platform_code_review/
async def async_setup(hass: HomeAssistant, config: ConfigType):
    _LOGGER.info("[async_setup] setting-up {DOMAIN}")
    """Set up the remote_homeassistant component."""
    component = hass.data[DOMAIN] = EntityComponent[ImmichImage](
        _LOGGER, DOMAIN, hass, SCAN_INTERVAL
    )

    hass.async_create_task(setup_view(hass, component))

    return True

async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry):
    """Set up Remote Home-Assistant from a config entry."""

    hub = ImmichHub(host=config.data[CONF_HOST], api_key=config.data[CONF_API_KEY])

    if not await hub.authenticate():
        raise InvalidAuth

    component: EntityComponent[ImmichImage] = hass.data[DOMAIN]
    return await component.async_setup_entry(config)


async def async_unload_entry(hass: HomeAssistant, config: ConfigEntry):
    component: EntityComponent[ImmichImage] = hass.data[DOMAIN]
    return await component.async_unload_entry(config)
