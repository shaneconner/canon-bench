"""Plain-text boxes for the CLI output."""


def wrap(text, width):
    if width < 1:
        raise ValueError("width must be positive")
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def box(lines, width=None):
    lines = list(lines)
    width = width or max((len(line) for line in lines), default=0)
    rule = "+" + "-" * (width + 2) + "+"
    body = ["| " + line.ljust(width)[:width] + " |" for line in lines]
    return [rule] + body + [rule]


def render(title, lines, width=None):
    width = width or max([len(title)] + [len(line) for line in lines] + [0])
    return box([title, "-" * width] + list(lines), width)
