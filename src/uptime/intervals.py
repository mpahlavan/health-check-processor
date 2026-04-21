from collections.abc import Iterable, Iterator

from .models import Interval, Ping, Status


def resolve_unknowns(pings: Iterable[Ping]) -> Iterator[Ping]:
    """Forward-fill UNKNOWN pings with the next definitive status.

    Buffers consecutive UNKNOWNs and emits them once a UP or DOWN ping
    is seen, replacing their status. Trailing UNKNOWNs with no successor
    are dropped entirely — they cannot be resolved per the spec.
    """
    pending: list[Ping] = []
    for ping in pings:
        if ping.status is Status.UNKNOWN:
            pending.append(ping)
        else:
            for p in pending:
                yield Ping(
                    timestamp=p.timestamp,
                    service_id=p.service_id,
                    status=ping.status,
                )
            pending.clear()
            yield ping
    # pending is non-empty only for trailing UNKNOWNs — drop them


def collapse_to_intervals(pings: Iterable[Ping]) -> Iterator[Interval]:
    """Collapse consecutive same-status pings into half-open intervals.

    Expects pings for a single service, sorted by timestamp, with no
    UNKNOWN statuses (run resolve_unknowns first). The final interval
    has end_time = -1 to signal it is still open.
    """
    current_status: Status | None = None
    start_time: int = 0

    for ping in pings:
        if ping.status is not current_status:
            if current_status is not None:
                yield Interval(
                    service_id=ping.service_id,
                    start_time=start_time,
                    end_time=ping.timestamp,
                    status=current_status,
                )
            current_status = ping.status
            start_time = ping.timestamp

    if current_status is not None:
        yield Interval(
            service_id=ping.service_id,  # type: ignore[possibly-undefined]
            start_time=start_time,
            end_time=-1,
            status=current_status,
        )
