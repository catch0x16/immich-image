from typing import final
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.httpx_client import get_async_client

from datetime import datetime

from .hub import ImmichHub, ImmichImage

ENTITY_IMAGE_URL = "/api/immich-image/{0}/{1}"

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Immich image platform."""

    hub = ImmichHub(
        host=config_entry.data[CONF_HOST], api_key=config_entry.data[CONF_API_KEY]
    )

    async_add_entities([TimelineImmichImageEntity(hass, hub)])

    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))

async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle options updates."""
    await hass.config_entries.async_reload(config_entry.entry_id)


class ImmichImageEntity(Entity):
    """The base class for image entities."""

    _entity_component_unrecorded_attributes = frozenset(
        {"asset_id"}
    )

    # Entity Properties
    _attr_content_type: str = ""
    _attr_image_last_updated: datetime | None = None
    _attr_image_url: str | None
    _attr_should_poll: bool = False  # No need to poll image entities
    _attr_state: None = None  # State is determined by last_updated
    _cached_image: ImmichImage | None = None

    def __init__(self, hass: HomeAssistant, verify_ssl: bool = False) -> None:
        """Initialize an image entity."""
        self._client = get_async_client(hass, verify_ssl=verify_ssl)

    @final
    @property
    def state(self) -> str | None:
        """Return the state."""
        return None

    @final
    @property
    def state_attributes(self) -> dict[str, str | None]:
        """Return the state attributes."""
        return {"asset_id": ""}


class TimelineImmichImageEntity(ImmichImageEntity):
    """Image entity for Immich that displays a random image from the user's timeline."""

    _attr_unique_id = "timeline_image"
    _attr_name = "Immich: Random timeline image"

    async def _refresh_available_asset_ids(self) -> list[str] | None:
        """Refresh the list of available asset IDs."""
        return [image["id"] for image in await self.hub.list_timeline_images()]