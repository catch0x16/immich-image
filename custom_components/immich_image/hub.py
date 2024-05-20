"""Hub for Immich integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import urljoin

import aiohttp

from homeassistant.exceptions import HomeAssistantError

_HEADER_API_KEY = "x-api-key"
_LOGGER = logging.getLogger(__name__)

_ALLOWED_MIME_TYPES = ["image/png", "image/jpeg", "image/heic"]

@dataclass
class ImmichImage:
    """Represent an image."""

    content_type: str
    content: bytes

class ImmichHub:
    """Immich API hub."""

    def __init__(self, host: str, api_key: str) -> None:
        """Initialize."""
        self.host = host
        self.api_key = api_key

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the host."""
        try:
            async with aiohttp.ClientSession() as session:
                url = urljoin(self.host, "/api/auth/validateToken")
                headers = {"Accept": "application/json", _HEADER_API_KEY: self.api_key}

                async with session.post(url=url, headers=headers) as response:
                    if response.status != 200:
                        raw_result = await response.text()
                        _LOGGER.error("Error from API: body=%s", raw_result)
                        return False

                    auth_result = await response.json()

                    if not auth_result.get("authStatus"):
                        raw_result = await response.text()
                        _LOGGER.error("Error from API: body=%s", raw_result)
                        return False

                    return True
        except aiohttp.ClientError as exception:
            _LOGGER.error("Error connecting to the API: %s", exception)
            raise CannotConnect from exception

    async def get_my_user_info(self) -> dict:
        """Get user info."""
        try:
            async with aiohttp.ClientSession() as session:
                url = urljoin(self.host, "/api/user/me")
                headers = {"Accept": "application/json", _HEADER_API_KEY: self.api_key}

                async with session.get(url=url, headers=headers) as response:
                    if response.status != 200:
                        raw_result = await response.text()
                        _LOGGER.error("Error from API: body=%s", raw_result)
                        raise ApiError()

                    user_info: dict = await response.json()

                    return user_info
        except aiohttp.ClientError as exception:
            _LOGGER.error("Error connecting to the API: %s", exception)
            raise CannotConnect from exception

    async def download_asset(self, asset_id: str) -> ImmichImage | None:
        """Download the asset."""
        try:
            async with aiohttp.ClientSession() as session:
                url = urljoin(self.host, f"/api/asset/file/{asset_id}")
                headers = {_HEADER_API_KEY: self.api_key}

                async with session.get(url=url, headers=headers) as response:
                    if response.status != 200:
                        _LOGGER.error("Error from API: status=%d", response.status)
                        return None

                    if response.content_type not in _ALLOWED_MIME_TYPES:
                        _LOGGER.error(
                            "MIME type is not supported: %s", response.content_type
                        )
                        return None

                    content = await response.read()
                    return ImmichImage(response.content_type, content)
        except aiohttp.ClientError as exception:
            _LOGGER.error("Error connecting to the API: %s", exception)
            raise CannotConnect from exception

    async def list_timeline_images(self) -> list[dict]:
        """List all timeline images."""
        try:
            async with aiohttp.ClientSession() as session:
                buckets_url = urljoin(self.host, "/api/timeline/buckets")
                headers = {"Accept": "application/json", _HEADER_API_KEY: self.api_key}
                buckets_params = {"isArchived": "false", "size": "MONTH", "withPartners": "true", "withStacked": "true"}

                async with session.get(url=buckets_url, headers=headers, params=buckets_params) as response:
                    if response.status != 200:
                        raw_result = await response.text()
                        _LOGGER.error("Error from API: body=%s", raw_result)
                        raise ApiError()

                    buckets: list[dict] = await response.json()

                    assets = []
                    for bucket in buckets:
                        bucket_url = urljoin(self.host, "/api/timeline/bucket")
                        bucket_params = {"isArchived": "false", "size": "MONTH", "withPartners": "true", "withStacked": "true", "timeBucket": bucket["timeBucket"]}
                        async with session.get(url=bucket_url, headers=headers, params=bucket_params) as response:
                            if response.status != 200:
                                raw_result = await response.text()
                                _LOGGER.error("Error from API: body=%s", raw_result)
                                raise ApiError()

                            bucket: list[dict] = await response.json()
                            for asset in bucket:
                                assets.append(asset)

                    filtered_assets: list[dict] = [
                        asset for asset in assets if asset["type"] == "IMAGE"
                    ]

                    return filtered_assets
        except aiohttp.ClientError as exception:
            _LOGGER.error("Error connecting to the API: %s", exception)
            raise CannotConnect from exception

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class ApiError(HomeAssistantError):
    """Error to indicate that the API returned an error."""