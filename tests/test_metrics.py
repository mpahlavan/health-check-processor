from uptime.metrics import compute_metrics, format_report
from uptime.models import Interval, Status


def test_compute_metrics_uptime_pct() -> None:
    intervals = [
        Interval("svc", 0, 900, Status.UP),
        Interval("svc", 900, 1000, Status.DOWN),
    ]
    m = compute_metrics(intervals)
    assert m["svc"].uptime_pct == 90.0
    assert m["svc"].outages == 1
    assert m["svc"].longest_outage == 100


def test_compute_metrics_open_interval_excluded() -> None:
    intervals = [Interval("svc", 0, -1, Status.UP)]
    m = compute_metrics(intervals)
    assert m["svc"].total_duration == 0
    assert m["svc"].uptime_pct == 100.0


def test_compute_metrics_no_outages() -> None:
    intervals = [
        Interval("svc", 0, 500, Status.UP),
        Interval("svc", 500, -1, Status.UP),
    ]
    m = compute_metrics(intervals)
    assert m["svc"].outages == 0
    assert m["svc"].longest_outage == 0


def test_compute_metrics_multiple_services() -> None:
    intervals = [
        Interval("a", 0, 1000, Status.UP),
        Interval("b", 0, 500, Status.DOWN),
    ]
    m = compute_metrics(intervals)
    assert "a" in m and "b" in m
    assert m["a"].uptime_pct == 100.0
    assert m["b"].outages == 1


def test_format_report_contains_service() -> None:
    intervals = [Interval("1", 0, 3600, Status.UP)]
    report = format_report(compute_metrics(intervals))
    assert "Service 1" in report
    assert "100.0%" in report


def test_format_report_shows_longest_outage() -> None:
    intervals = [Interval("1", 0, 7200, Status.DOWN)]
    report = format_report(compute_metrics(intervals))
    assert "2h" in report


def test_format_report_empty() -> None:
    report = format_report({})
    assert report == "=== Uptime Report ==="
