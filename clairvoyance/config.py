from clairvoyance.entities.context import config_ctx
from clairvoyance.entities.interfaces import IConfig


# pylint: disable=too-few-public-methods
class Config(IConfig):

    def __init__(self) -> None:
        self._bucket_size: int = 64

        config_ctx.set(self)
