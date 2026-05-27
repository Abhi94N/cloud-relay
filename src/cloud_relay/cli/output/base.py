"""The formatter protocol.

A :class:`Formatter` turns a Pydantic model (or list of models) into a string
for display. Concrete formatters live alongside this module, one per format,
and are registered in :mod:`cloud_relay.cli.output`.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class Formatter(Protocol):
    """Renders models to a displayable string."""

    def render(
        self, data: BaseModel | Sequence[BaseModel], *, show_secret: bool = False
    ) -> str:
        """Render ``data`` to a string.

        Args:
            data: A single model or a list of models.
            show_secret: When True, reveal masked secret fields.

        Returns:
            The formatted string ready to print.
        """
        ...
