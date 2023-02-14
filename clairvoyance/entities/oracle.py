"""Oracle definitions."""

from enum import Enum


class FuzzingContext(str, Enum):

    """Contexts."""
    ARGUMENT = 'InputValue'
    FIELD = 'Field'
