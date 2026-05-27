"""Output formatter registry and entry point.

Commands call :func:`render` with the data and the chosen format name; they
never format or print directly. Adding a new format is a new module plus one
line in :data:`_REGISTRY`.
"""

from collections.abc import Sequence

from pydantic import BaseModel

from cloud_relay.cli.output.base import Formatter
from cloud_relay.cli.output.json import JsonFormatter
from cloud_relay.cli.output.table import TableFormatter
from cloud_relay.cli.output.yaml import YamlFormatter

_REGISTRY: dict[str, Formatter] = {
    "json": JsonFormatter(),
    "table": TableFormatter(),
    "yaml": YamlFormatter(),
}


def available_formats() -> list[str]:
    """Return the list of registered format names."""
    return list(_REGISTRY)


def render(
    data: BaseModel | Sequence[BaseModel],
    fmt: str,
    *,
    show_secret: bool = False,
) -> str:
    """Render ``data`` in the named format.

    Args:
        data: A single model or list of models to render.
        fmt: One of the registered format names (see :func:`available_formats`).
        show_secret: When True, reveal masked secret fields.

    Returns:
        The formatted string.

    Raises:
        ValueError: If ``fmt`` is not a registered format.
    """
    try:
        formatter = _REGISTRY[fmt]
    except KeyError:
        raise ValueError(
            f"unknown output format: {fmt!r} (choose from {', '.join(_REGISTRY)})"
        ) from None
    return formatter.render(data, show_secret=show_secret)
