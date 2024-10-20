"""Public Transport Victoria API client."""
import asyncio
import datetime
import hmac
from hashlib import sha1
from typing import Any, Dict, Optional

import aiohttp
from homeassistant.core import HomeAssistant

BASE_URL = "https://timetableapi.ptv.vic.gov.au"

class PTVApiClient:
    """Public Transport Victoria API client."""

    def __init__(self, hass: HomeAssistant, dev_id: str, api_key: str):
        """Initialize the API client."""
        self.hass = hass
        self.dev_id = dev_id
        self.api_key = api_key
        self.session = hass.helpers.aiohttp_client.async_get_clientsession()

    def _build_url(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Build the URL for API requests."""
        url = f"{BASE_URL}{path}"
        if params:
            url += ('&' if '?' in url else '?') + '&'.join(f"{k}={v}" for k, v in params.items())
        
        url += ('&' if '?' in url else '?') + f"devid={self.dev_id}"
        
        raw = url.split(BASE_URL)[1]
        hashed = hmac.new(self.api_key.encode('utf-8'), raw.encode('utf-8'), sha1)
        signature = hashed.hexdigest()
        
        return f"{url}&signature={signature}"

    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make an API request."""
        url = self._build_url(path, kwargs.get('params'))
        async with self.session.request(method, url, **kwargs) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """Make a GET request to the API."""
        return await self._request("GET", path, **kwargs)

# We'll add more specific API methods in separate files
