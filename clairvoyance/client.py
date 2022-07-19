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
        document: Optional[str],
    ) -> Dict:
        """Post a GraphQL document to the server and return the response as JSON."""

        if not self._session:
            self._session = aiohttp.ClientSession(headers=self._headers)

        gql_document = None
        if document:
            gql_document = {'query': document}

        response = await self._session.post(
            self._url,
            json=gql_document,
        )

        return await response.json()
