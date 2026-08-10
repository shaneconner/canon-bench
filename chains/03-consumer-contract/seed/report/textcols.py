"""Plain-text column layout, left over from the old operations digest.

Nothing in the nightly path imports this any more; the digest script that did
was retired, but the helpers are still the least awful way to line up columns
in a terminal.
"""


def widths(rows):
    columns = max((len(row) for row in rows), default=0)
    return [max((len(str(row[i])) for row in rows if i < len(row)), default=0)
            for i in range(columns)]


def render(rows, gutter=2, align=None):
    """Render rows of cells as space-padded columns."""
    sizes = widths(rows)
    align = align or []
    lines = []
    for row in rows:
        cells = []
        for index, cell in enumerate(row):
            text = str(cell)
            how = align[index] if index < len(align) else "left"
            cells.append(text.rjust(sizes[index]) if how == "right" else text.ljust(sizes[index]))
        lines.append((" " * gutter).join(cells).rstrip())
    return lines


def rule(rows, character="-"):
    return (" " * 2).join(character * size for size in widths(rows))
