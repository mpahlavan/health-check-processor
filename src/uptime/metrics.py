from dataclasses import dataclass

from .models import Interval, Status


@dataclass
class ServiceMetrics:
    service_id: str
    total_duration: int
    up_duration: int
    outages: int
    longest_outage: int  # seconds; 0 if no outages

    @property
    def uptime_pct(self) -> float:
        if self.total_duration == 0:
            return 100.0
        return 100.0 * self.up_duration / self.total_duration


def compute_metrics(intervals: list[Interval]) -> dict[str, ServiceMetrics]:
    """Per-service uptime %, total outages, and longest outage duration.

    Open intervals (end_time == -1) are excluded from duration calculations
    since their true length is unknown.
    """
    metrics: dict[str, ServiceMetrics] = {}

    for iv in intervals:
        if iv.service_id not in metrics:
            metrics[iv.service_id] = ServiceMetrics(
                service_id=iv.service_id,
                total_duration=0,
                up_duration=0,
                outages=0,
                longest_outage=0,
            )

        m = metrics[iv.service_id]

        if iv.end_time == -1:
            continue  # open interval — duration unknown

        duration = iv.end_time - iv.start_time
        m.total_duration += duration

        if iv.status is Status.UP:
            m.up_duration += duration
        else:
            m.outages += 1
            m.longest_outage = max(m.longest_outage, duration)

    return metrics


def format_report(metrics: dict[str, ServiceMetrics]) -> str:
    lines = ["=== Uptime Report ==="]
    for svc_id in sorted(metrics):
        m = metrics[svc_id]
        line = f"Service {svc_id}: {m.uptime_pct:5.1f}% UP  |  outages: {m.outages}"
        if m.longest_outage:
            h, rem = divmod(m.longest_outage, 3600)
            mins = rem // 60
            line += f"  |  longest outage: {h}h {mins:02d}m"
        lines.append(line)
    return "\n".join(lines)
