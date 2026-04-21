from itertools import groupby

from uptime.intervals import collapse_to_intervals, resolve_unknowns
from uptime.models import Interval, Ping


def process(pings: list[Ping]) -> list[Interval]:
    """Minimal pipeline: sort → group by service → resolve → collapse → sort output."""
    sorted_pings = sorted(pings, key=lambda p: (p.service_id, p.timestamp))
    result: list[Interval] = []
    for _, group in groupby(sorted_pings, key=lambda p: p.service_id):
        resolved = resolve_unknowns(group)
        result.extend(collapse_to_intervals(resolved))
    return sorted(result, key=lambda i: (i.service_id, i.start_time))
