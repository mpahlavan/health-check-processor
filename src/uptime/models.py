from dataclasses import dataclass
from enum import Enum


class Status(Enum):
    UP = "UP"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Ping:
    timestamp: int
    service_id: str
    status: Status


@dataclass(frozen=True)
class Interval:
    service_id: str
    start_time: int
    end_time: int  # -1 means open (no subsequent ping for this service)
    status: Status  # always UP or DOWN in output
