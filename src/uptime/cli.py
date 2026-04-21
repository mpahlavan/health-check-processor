import argparse
import logging
import sys
from itertools import groupby
from pathlib import Path

from .intervals import collapse_to_intervals, resolve_unknowns
from .io import read_pings, write_intervals
from .metrics import compute_metrics, format_report
from .models import Interval, Ping


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uptime",
        description="Convert monitoring pings CSV to service uptime intervals CSV.",
    )
    parser.add_argument("--input", required=True, metavar="PATH", help="input CSV file")
    parser.add_argument(
        "--output",
        metavar="PATH",
        default=None,
        help="output CSV file (default: stdout)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="print per-service uptime metrics to stderr",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase log verbosity (-v WARNING, -vv INFO, -vvv DEBUG)",
    )
    return parser


def _pipeline(pings: list[Ping]) -> list[Interval]:
    sorted_pings = sorted(pings, key=lambda p: (p.service_id, p.timestamp))
    result: list[Interval] = []
    for _, group in groupby(sorted_pings, key=lambda p: p.service_id):
        resolved = resolve_unknowns(group)
        result.extend(collapse_to_intervals(resolved))
    return sorted(result, key=lambda i: (i.service_id, i.start_time))


_VERBOSITY = {0: logging.WARNING, 1: logging.WARNING, 2: logging.INFO, 3: logging.DEBUG}


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    level = _VERBOSITY.get(args.verbose, logging.DEBUG)
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None

    pings = list(read_pings(input_path))
    intervals = _pipeline(pings)

    write_intervals(intervals, output_path)

    if args.report:
        metrics = compute_metrics(intervals)
        print(format_report(metrics), file=sys.stderr)
