"""
Initialize Immich Image
"""
import logging

from homeassistant.const import CONF_HOST

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.setup import async_setup_component

from custom_components.immich_image.views import ImmichImageView
from .const import DOMAIN, CONF_HUBS
from .hub import ImmichHub, InvalidAuth

_LOGGER = logging.getLogger(__name__)

async def setup_view(hass: HomeAssistant):
    _LOGGER.info("[setup_view] setting-up {DOMAIN}")
    hass.http.register_view(ImmichImageView(None))

# https://developers.home-assistant.io/docs/creating_platform_code_review/
async def async_setup(hass: HomeAssistant, config: ConfigType):
    _LOGGER.info("[async_setup] setting-up {DOMAIN}")
    """Set up the remote_homeassistant component."""
    hass.data.setdefault(DOMAIN, {})

    hass.async_create_task(setup_view(hass))

    return True

async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry):
    """Set up Remote Home-Assistant from a config entry."""

    hub = ImmichHub(host=config.data[CONF_HOST], api_key=config.data[CONF_API_KEY])

    if not await hub.authenticate():
        raise InvalidAuth

    hass.data[DOMAIN][config.entry_id] = hub

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id)

    return True
