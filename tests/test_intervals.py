from conftest import process
from uptime.intervals import resolve_unknowns
from uptime.models import Interval, Ping, Status

# ---------------------------------------------------------------------------
# Test data
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


# ---------------------------------------------------------------------------
# Golden test
# ---------------------------------------------------------------------------


def test_pdf_sample() -> None:
    assert process(SAMPLE_PINGS) == EXPECTED_INTERVALS


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_trailing_unknown_is_dropped() -> None:
    pings = [
        Ping(1000, "svc", Status.UP),
        Ping(2000, "svc", Status.UNKNOWN),  # no successor — must be dropped
    ]
    result = list(resolve_unknowns(pings))
    assert all(p.status is not Status.UNKNOWN for p in result)
    assert len(result) == 1


def test_leading_unknowns_resolve_to_next_status() -> None:
    pings = [
        Ping(1000, "svc", Status.UNKNOWN),
        Ping(2000, "svc", Status.UNKNOWN),
        Ping(3000, "svc", Status.DOWN),
    ]
    result = list(resolve_unknowns(pings))
    assert len(result) == 3
    assert all(p.status is Status.DOWN for p in result)


def test_single_ping_gives_open_interval() -> None:
    pings = [Ping(1000, "svc", Status.UP)]
    assert process(pings) == [Interval("svc", 1000, -1, Status.UP)]


def test_all_unknown_service_produces_no_output() -> None:
    pings = [
        Ping(1000, "svc", Status.UNKNOWN),
        Ping(2000, "svc", Status.UNKNOWN),
    ]
    assert process(pings) == []


def test_empty_input() -> None:
    assert process([]) == []


def test_consecutive_same_status_is_one_interval() -> None:
    pings = [
        Ping(1000, "svc", Status.UP),
        Ping(2000, "svc", Status.UP),
        Ping(3000, "svc", Status.UP),
    ]
    assert process(pings) == [Interval("svc", 1000, -1, Status.UP)]
