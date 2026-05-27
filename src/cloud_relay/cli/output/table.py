"""Rich table output formatter."""

from collections.abc import Sequence

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table


class TableFormatter:
    """Renders models as a Rich table (one row per model).

    Columns are taken from the fields of the first model. Secret fields are
    masked unless ``show_secret`` is True.
    """

    def render(
        self, data: BaseModel | Sequence[BaseModel], *, show_secret: bool = False
    ) -> str:
        """Render ``data`` as a table string. See :class:`Formatter`."""
        rows = [data] if isinstance(data, BaseModel) else list(data)
        ctx = {"show_secret": show_secret}
        if not rows:
            return "(no results)"

        dumped = [m.model_dump(mode="json", context=ctx) for m in rows]
        columns = list(dumped[0].keys())

        table = Table(show_header=True, header_style="bold")
        for col in columns:
            table.add_column(col)
        for row in dumped:
            table.add_row(*(str(row.get(col, "")) for col in columns))

        # Render the table to a string via a Console capture so the formatter
        # contract (return str) holds regardless of where output is sent.
        console = Console(record=True)
        with console.capture() as capture:
            console.print(table)
        return capture.get()
