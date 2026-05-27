"""YAML output formatter."""

from collections.abc import Sequence
from typing import Any

import yaml
from pydantic import BaseModel


class YamlFormatter:
    """Renders models as YAML, with the same secret-masking behavior as JSON."""

    def render(
        self, data: BaseModel | Sequence[BaseModel], *, show_secret: bool = False
    ) -> str:
        """Render ``data`` as a YAML string. See :class:`Formatter`."""
        ctx = {"show_secret": show_secret}

        def dump(m: BaseModel) -> dict[str, Any]:
            return m.model_dump(mode="json", context=ctx)

        payload: Any = (
            dump(data) if isinstance(data, BaseModel) else [dump(m) for m in data]
        )
        return yaml.safe_dump(payload, sort_keys=False, default_flow_style=False)
