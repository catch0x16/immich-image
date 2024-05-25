from __future__ import annotations

import asyncio
from typing import final
import logging
import hashlib

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.httpx_client import get_async_client

from datetime import datetime, timedelta

from .hub import ImmichHub, ImmichImage


# How often to refresh the list of available asset IDs
ID_LIST_REFRESH_INTERVAL = timedelta(hours=12)
ENTITY_IMAGE_URL = "/api/immich-image/{0}/{1}"

_LOGGER = logging.getLogger(__name__)

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
        {"asset_id", "asset_ids", "image_url"}
    )

    # We want to get a new image every so often, as defined by the refresh interval
    _attr_should_poll = True
    _attr_has_entity_name = True

    # Entity Properties
    _asset_id_last_updated: datetime | None = None
    _attr_state: None = None  # State is determined by last_updated

    _asset_ids: list[str] | None = []
    _asset_ids_last_updated: datetime | None = None

    _asset_id_hash: str | None

    _cached_images: dict[str, ImmichImage] = {}

    hub: ImmichHub

    def __init__(self, hass: HomeAssistant, hub: ImmichHub, verify_ssl: bool = False) -> None:
        """Initialize an image entity."""
        self._client = get_async_client(hass, verify_ssl=verify_ssl)
        self.hub = hub

    @property
    @final
    def state(self) -> str | None:
        """Return the state."""
        return self._asset_id_hash

    @final
    @property
    def state_attributes(self) -> dict[str, str | None]:
        """Return the state attributes."""
        image_urls = [ENTITY_IMAGE_URL.format(self.entity_id, asset_id) for asset_id in self._asset_ids]
        return {"image_urls":  ",".join(image_urls)}

    def calculate_hash(self) -> str:
        m = hashlib.sha256()
        for asset_id in self._asset_ids:
            m.update(str.encode(asset_id))
        return m.hexdigest()

    async def async_update(self) -> None:
        if (
            not self._asset_ids_last_updated
            or (datetime.now() - self._asset_ids_last_updated)
            > ID_LIST_REFRESH_INTERVAL
        ):
            # If we don't have any available asset IDs yet, or the list is stale, refresh it
            _LOGGER.debug("Refreshing asset Ids")
            self._asset_ids = await self._refresh_asset_ids()
            self._asset_id_hash = self.calculate_hash()
            self._asset_ids_last_updated = datetime.now()

        if not self._asset_ids:
            # If we still don't have any available asset IDs, that's a problem
            _LOGGER.error("No assets are available")
            return None

    async def _refresh_asset_ids(self) -> list[str] | None:
        """Refresh the list of available asset IDs."""
        raise NotImplementedError

    async def async_load_image(self, asset_id: str, timeout: int) -> ImmichImage:
        """Download and cache the image."""
        if asset_id in self._cached_images:
            return self._cached_images[asset_id]

        image: ImmichImage = None
        async with asyncio.timeout(timeout):
            while not image:
                image  = await self.hub.download_asset(asset_id)
                if not image:
                    await asyncio.sleep(1)
                    continue
                self._cached_images[asset_id] = image
        return image

class TimelineImmichImageEntity(ImmichImageEntity):
    """Image entity for Immich that displays a random image from the user's timeline."""

    _attr_unique_id = "timeline_image"
    _attr_name = "Immich: Random timeline image"

    async def _refresh_asset_ids(self) -> list[str] | None:
        """Refresh the list of asset Ids."""
        return [image["id"] for image in await self.hub.list_timeline_images()]