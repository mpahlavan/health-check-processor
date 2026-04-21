from collections.abc import Iterable, Iterator

from .models import Ping, Status


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
