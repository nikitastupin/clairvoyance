import asyncio
import logging
from typing import Dict, Optional

import aiohttp


class Client:

    _url: str
    _headers: Dict[str, str]
    _max_retries: int

    _session: Optional[aiohttp.ClientSession]
    _semaphore: asyncio.Semaphore
    _logger: logging.Logger

    def __init__(
        self,
        url: str,
        headers: Dict[str, str],
        logger: logging.Logger,
        max_retries: int = 3,
    ) -> None:
        self._url = url
        self._headers = headers
        self._max_retries = max_retries

        self._session = None
        self._semaphore = asyncio.Semaphore(50)
        self._logger = logger

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
                self._session = aiohttp.ClientSession(headers=self._headers)

            gql_document = None
            if document:
                gql_document = {'query': document}

            try:
                response = await self._session.post(
                    self._url,
                    json=gql_document,
                )
                body = await response.json()
                return body

            except (aiohttp.client_exceptions.ClientConnectionError, aiohttp.client_exceptions.ClientPayloadError) as e:
                self._logger.warning(f'Error posting to {self._url}: {e}')

        return await self.post(document, retries + 1)

    async def close(self) -> None:
        if self._session:
            await self._session.close()
