from itertools import groupby

from hypothesis import given
from hypothesis import strategies as st

from uptime.models import Ping, Status

from conftest import process

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_status_st = st.sampled_from(Status)
_service_id_st = st.sampled_from(["1", "2", "3"])
_timestamp_st = st.integers(min_value=1, max_value=10**10)

_ping_st = st.builds(
    Ping,
    timestamp=_timestamp_st,
    service_id=_service_id_st,
    status=_status_st,
)

_ping_list_st = st.lists(_ping_st, min_size=0, max_size=100)

# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


@given(_ping_list_st)
def test_output_never_contains_unknown(pings: list[Ping]) -> None:
    result = process(pings)
    assert all(i.status is not Status.UNKNOWN for i in result)


@given(_ping_list_st)
def test_intervals_are_contiguous(pings: list[Ping]) -> None:
    result = process(pings)
    for _, grp in groupby(result, key=lambda i: i.service_id):
        group = list(grp)
        for a, b in zip(group, group[1:]):
            assert a.end_time == b.start_time


@given(_ping_list_st)
def test_interval_count_leq_ping_count(pings: list[Ping]) -> None:
    assert len(process(pings)) <= len(pings)
