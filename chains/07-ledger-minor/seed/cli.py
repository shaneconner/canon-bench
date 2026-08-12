#!/usr/bin/env python3
"""Command line entry point."""
import sys
from pathlib import Path

from ops import receiving, refunds, returns
from promo import credits

WORKDIR = Path(__file__).resolve().parent

USAGE = "usage: cli.py <refund|credit|return|receive> ..."


def main(argv):
    if len(argv) < 2:
        print(USAGE)
        return 2
    command, args = argv[1], argv[2:]
    try:
        if command == "refund" and len(args) == 3:
            print(refunds.refund_amount(args[0], args[1], args[2]))
            return 0
        if command == "credit" and len(args) == 3:
            print(credits.issue_credit(WORKDIR, args[0], args[1], args[2]))
            return 0
        if command == "return" and len(args) == 3:
            print(returns.accept_return(WORKDIR, args[0], args[1], args[2]))
            return 0
        if command == "receive" and len(args) == 3:
            print(receiving.receive_shipment(WORKDIR, args[0], args[1], args[2]))
            return 0
    except ValueError as error:
        print(f"error: {error}")
        return 1
    print(USAGE)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
