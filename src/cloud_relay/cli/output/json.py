"""JSON output formatter."""

import json
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel


class JsonFormatter:
    """Renders models as indented JSON.

    Secret fields are revealed only when ``show_secret`` is True; this is
    threaded into Pydantic via serialization ``context`` and honored by the
    model's field serializer.
    """

    def render(
        self, data: BaseModel | Sequence[BaseModel], *, show_secret: bool = False
    ) -> str:
        """Render ``data`` as a JSON string. See :class:`Formatter`."""
        ctx = {"show_secret": show_secret}

        def dump(m: BaseModel) -> dict[str, Any]:
            return m.model_dump(mode="json", context=ctx)

        payload: Any = (
            dump(data) if isinstance(data, BaseModel) else [dump(m) for m in data]
        )
        return json.dumps(payload, indent=2, default=str)
