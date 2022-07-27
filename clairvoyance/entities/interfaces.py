# pylint: disable=too-few-public-methods

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Optional

import aiohttp


class IConfig(ABC):

    _bucket_size: int

    @property
    def bucket_size(self) -> int:
        return self._bucket_size


class IClient(ABC):
    _url: str
    _headers: Dict[str, str]
    _max_retries: int

    _session: Optional[aiohttp.ClientSession]
    _semaphore: asyncio.Semaphore

    @abstractmethod
    async def post(
        self,
        document: Optional[str],
        retries: int = 0,
    ) -> Dict:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...
