"""Reference codes for the settlement upload.

A code is a base-36 body plus a two-character mod-97 check suffix. The
settlement tool hands these back to us verbatim, so encode and decode have to
stay exact inverses.
"""

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def to_base36(number):
    if number == 0:
        return "0"
    digits = []
    while number:
        number, remainder = divmod(number, 36)
        digits.append(ALPHABET[remainder])
    return "".join(reversed(digits))


def from_base36(text):
    value = 0
    for character in text:
        value = value * 36 + ALPHABET.index(character)
    return value


def check_digits(body):
    return f"{98 - (from_base36(body) * 100) % 97:02d}"


def encode(number):
    body = to_base36(number)
    return f"{body}{check_digits(body)}"


def decode(code):
    body, suffix = code[:-2], code[-2:]
    if suffix != check_digits(body):
        raise ValueError(f"bad check digits in reference code {code!r}")
    return from_base36(body)
