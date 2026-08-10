"""Plain-text table helpers for the report."""


def column_width(cells):
    return max((len(str(cell)) for cell in cells), default=0)


def render_row(cells, widths, sep="  "):
    return sep.join(str(cell).ljust(width) for cell, width in zip(cells, widths)).rstrip()


def render(headers, rows):
    grid = [list(headers)] + [list(row) for row in rows]
    widths = [column_width(column) for column in zip(*grid)]
    lines = [render_row(headers, widths), render_row(["-" * width for width in widths], widths)]
    lines.extend(render_row(row, widths) for row in rows)
    return "\n".join(lines)


class Table:
    """A table with fixed headers, so a surface can hold on to one and reuse it."""

    def __init__(self, headers):
        self.headers = list(headers)

    def render(self, rows):
        return render(self.headers, rows)
