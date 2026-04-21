from itertools import groupby

from uptime.intervals import collapse_to_intervals, resolve_unknowns
from uptime.models import Interval, Ping, Status

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_PINGS = [
    Ping(1767951572, "1", Status.UP),
    Ping(1767558032, "1", Status.DOWN),
    Ping(1768184811, "1", Status.UP),
    Ping(1768280666, "2", Status.UP),
    Ping(1768789071, "1", Status.UP),
    Ping(1766478924, "2", Status.UP),
    Ping(1767400524, "1", Status.UP),
    Ping(1767340434, "2", Status.UNKNOWN),
    Ping(1768760587, "1", Status.UP),
    Ping(1767131604, "2", Status.UP),
]

EXPECTED_INTERVALS = [
    Interval("1", 1767400524, 1767558032, Status.UP),
    Interval("1", 1767558032, 1767951572, Status.DOWN),
    Interval("1", 1767951572, -1, Status.UP),
    Interval("2", 1766478924, -1, Status.UP),
]


def _process(pings: list[Ping]) -> list[Interval]:
    """Minimal pipeline: sort → group → resolve → collapse → sort output."""
    sorted_pings = sorted(pings, key=lambda p: (p.service_id, p.timestamp))
    result: list[Interval] = []
    for _, group in groupby(sorted_pings, key=lambda p: p.service_id):
        resolved = resolve_unknowns(group)
        result.extend(collapse_to_intervals(resolved))
    return sorted(result, key=lambda i: (i.service_id, i.start_time))


# ---------------------------------------------------------------------------
# Golden test
# ---------------------------------------------------------------------------


def test_pdf_sample() -> None:
    assert _process(SAMPLE_PINGS) == EXPECTED_INTERVALS
