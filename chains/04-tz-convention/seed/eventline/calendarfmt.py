"""Display helpers. Everything here is for humans reading a terminal."""


def stamp(value):
    return value.strftime("%Y-%m-%d %H:%M")


def day_label(day):
    return day.strftime("%a %d %b")


def duration(minutes):
    hours, rest = divmod(int(minutes), 60)
    if hours and rest:
        return f"{hours}h {rest}m"
    if hours:
        return f"{hours}h"
    return f"{rest}m"


def line(event):
    return f"{stamp(event['starts_at'])}  {event['title']}  ({duration(event['duration_min'])})"
