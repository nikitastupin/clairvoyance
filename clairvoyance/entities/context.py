import logging
from contextvars import ContextVar
from typing import Callable

from clairvoyance.entities.interfaces import IClient, IConfig

config_ctx: ContextVar[IConfig] = ContextVar('config')
client_ctx: ContextVar[IClient] = ContextVar('client')
logger_ctx: ContextVar[logging.Logger] = ContextVar('logger')

# Quick resolve the context variables using macros.
config: Callable[..., IConfig] = lambda: config_ctx.get()  # pylint: disable=unnecessary-lambda
client: Callable[..., IClient] = lambda: client_ctx.get()  # pylint: disable=unnecessary-lambda
log: Callable[..., logging.Logger] = lambda: logger_ctx.get()  # pylint: disable=unnecessary-lambda
