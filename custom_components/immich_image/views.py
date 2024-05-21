"""The immich image view integration."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass

from homeassistant.components.http import KEY_AUTHENTICATED, KEY_HASS, HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_component import EntityComponent

from aiohttp import hdrs, web

from .const import IMAGE_TIMEOUT, DOMAIN
from .hub import ImmichHub, ImmichImage


@dataclass
class Image:
    """Represent an image."""

    content_type: str
    content: bytes


class ImageContentTypeError(HomeAssistantError):
    """Error with the content type while loading an image."""


def valid_image_content_type(content_type: str | None) -> str:
    """Validate the assigned content type is one of an image."""
    if content_type is None or content_type.split("/", 1)[0] != "image":
        raise ImageContentTypeError
    return content_type


class ImmichImageView(HomeAssistantView):
    """Get all logged errors and warnings."""

    url = "/api/immich-image/{entity_id}/{asset_id}"
    name = "api:immich-image:image"
    requires_auth = False

    component: EntityComponent[ImmichImage]

    def __init__(self, component) -> None:
        """Initialize an image view."""
        self.component = component

    async def get(
        self, request: web.Request, entity_id: str, asset_id: str
    ) -> web.StreamResponse:
        """Start a GET request."""
        image_entity = self.component.get_entity(entity_id)
        if image_entity is None:
            raise web.HTTPNotFound

        # authenticated = (
        #     request[KEY_AUTHENTICATED]
        #     or request.query.get("token") in image_entity.access_tokens
        # )

        # if not authenticated:
        # Attempt with invalid bearer token, raise unauthorized
        # so ban middleware can handle it.
        # if hdrs.AUTHORIZATION in request.headers:
        # raise web.HTTPUnauthorized
        # Invalid sigAuth or image entity access token
        # raise web.HTTPForbidden

        return await self.handle(request, entity_id, asset_id)

    async def handle(
        self, request: web.Request, entity_id: str, asset_id: str
    ) -> web.StreamResponse:
        """Serve image."""
        try:
            image = await self._async_get_image(asset_id, IMAGE_TIMEOUT)
        except (HomeAssistantError, ValueError) as ex:
            raise web.HTTPInternalServerError from ex

        return web.Response(body=image.content, content_type=image.content_type)

    async def _async_get_image(self, asset_id: str, timeout: int) -> Image:
        """Fetch image from an image entity."""
        with suppress(asyncio.CancelledError, TimeoutError, ImageContentTypeError):
            async with asyncio.timeout(timeout):
                if image := await self.hub.download_asset(asset_id):
                    content_type = valid_image_content_type(image.content_type)
                    return Image(content_type, image.content)

        raise HomeAssistantError("Unable to get image")
