from enum import EnumMeta
from typing import Any, Type


class MetaEnum(EnumMeta):

    """Meta class for Enum."""

    # pylint: disable=no-value-for-parameter
    def __contains__(
        cls: Type[Any],
        obj: object,
    ) -> bool:
        """Check if the object is in the enum using `in` keyword."""

        try:
            cls(obj)
        except ValueError:
            return False

        return True
