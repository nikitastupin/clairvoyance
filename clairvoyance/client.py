import aiohttp

from typing import Dict, Optional


class Client:

    _url: str
    _headers: Dict[str, str]

    _session: Optional[aiohttp.ClientSession]

    def __init__(
        self,
        url: str,
        headers: Dict[str, str],
    ) -> None:
        self._url = url
        self._headers = headers
        self._session = None

    async def post(
        self,
        document: Optional[Dict],
    ) -> aiohttp.ClientResponse:
        if not self._session:
            self._session = aiohttp.ClientSession(headers=self._headers)

        if document:
            document = {'query': document}

        return await self._session.post(self._url, json=document)
