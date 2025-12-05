import asyncio
import json
from typing import Dict, Optional

import aiohttp

from clairvoyance.entities.context import client_ctx, log
from clairvoyance.entities.interfaces import IClient


class Client(IClient):  # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        url: str,
        max_retries: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        concurrent_requests: Optional[int] = None,
        proxy: Optional[str] = None,
        backoff: Optional[int] = None,
        disable_ssl_verify: Optional[bool] = None,
    ) -> None:
        self._url = url
        self._session = None

        self._headers = headers or {}
        self._max_retries = max_retries or 3
        self._semaphore = asyncio.Semaphore(concurrent_requests or 50)
        self.proxy = proxy
        self.backoff = backoff
        self._backoff_semaphore = asyncio.Lock()
        self.disable_ssl_verify = disable_ssl_verify or False

        client_ctx.set(self)

    async def post(
        self,
        document: Optional[str],
        retries: int = 0,
    ) -> Dict:
        """Post a GraphQL document to the server and return the response as JSON."""

        if retries >= self._max_retries:
            return {}

        async with self._semaphore:
            if not self._session:
                connector = aiohttp.TCPConnector(ssl=not self.disable_ssl_verify)
                self._session = aiohttp.ClientSession(
                    headers=self._headers, connector=connector
                )

            # Translate an existing document into a GraphQL request.
            gql_document = {"query": document} if document else None
            try:
                response = await self._session.post(
                    self._url,
                    json=gql_document,
                    proxy=self.proxy,
                )

                if response.status >= 500:
                    log().warning(f"Received status code {response.status}")
                    return await self.post(document, retries + 1)

                try:
                    return await response.json(content_type=None)
                except json.decoder.JSONDecodeError as e:
                    log().warning(
                        f"JSON decode error while decoding response from {self._url} (status code: {response.status}): {e}"
                    )
                    log().debug(
                        "[Hint] Endpoint might require authentication, or, site is behind something like Cloudflare and is rate limiting you. "
                        "You can pass headers and cookies via -H option. Consult "
                        "https://github.com/nikitastupin/clairvoyance/blob/main/troubleshooting.md for more information."
                    )

            except (
                aiohttp.ClientConnectionError,
                aiohttp.ClientPayloadError,
                asyncio.TimeoutError,
            ) as e:
                log().warning(f"Connection error while POSTing to {self._url}: {e}")

            if self.backoff:
                async with self._backoff_semaphore:
                    delay = 0.5 * self.backoff**retries
                    log().debug(f"Waiting for backoff {delay} seconds.")
                    await asyncio.sleep(delay)

        return await self.post(document, retries + 1)

    async def close(self) -> None:
        if self._session:
            await self._session.close()
