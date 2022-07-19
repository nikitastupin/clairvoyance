import logging

from typing import Dict, Optional
from clairvoyance.client import Client


class Config:

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._url: str = url
        self._headers: dict[str, str] = headers or {}
        self._logger = logger or logging.getLogger('clairvoyance')
        self._bucket_size: int = 512

        self._client = Client(
            self._url,
            self._headers,
        )

    @property
    def client(self) -> Client:
        return self._client

    @property
    def log(self) -> logging.Logger:
        return self._logger

    @property
    def bucket_size(self) -> int:
        return self._bucket_size
