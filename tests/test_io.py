import logging
from pathlib import Path

import pytest

from uptime.io import read_pings, write_intervals
from uptime.models import Interval, Ping, Status


def _write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# read_pings
# ---------------------------------------------------------------------------


def test_read_valid_csv(tmp_path: Path) -> None:
    csv = _write_csv(
        tmp_path / "input.csv",
        "timestamp,service_id,response_time,status\n"
        "1000,svc1,50,UP\n"
        "2000,svc1,0,DOWN\n",
    )
    result = list(read_pings(csv))
    assert result == [
        Ping(1000, "svc1", Status.UP),
        Ping(2000, "svc1", Status.DOWN),
    ]


def test_read_empty_file_exits_2(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "empty.csv", "")
    with pytest.raises(SystemExit) as exc:
        list(read_pings(csv))
    assert exc.value.code == 2


def test_read_missing_column_exits_2(tmp_path: Path) -> None:
    csv = _write_csv(
        tmp_path / "bad.csv",
        "timestamp,service_id,status\n1000,svc1,UP\n",  # missing response_time
    )
    with pytest.raises(SystemExit) as exc:
        list(read_pings(csv))
    assert exc.value.code == 2


def test_read_unknown_status_is_skipped(tmp_path: Path) -> None:
    csv = _write_csv(
        tmp_path / "input.csv",
        "timestamp,service_id,response_time,status\n"
        "1000,svc1,50,UP\n"
        "2000,svc1,0,TYPO\n"
        "3000,svc1,10,DOWN\n",
    )
    result = list(read_pings(csv))
    assert len(result) == 2
    assert result[0].status is Status.UP
    assert result[1].status is Status.DOWN


def test_read_invalid_timestamp_is_skipped(tmp_path: Path) -> None:
    csv = _write_csv(
        tmp_path / "input.csv",
        "timestamp,service_id,response_time,status\n"
        "not_a_number,svc1,50,UP\n"
        "2000,svc1,0,DOWN\n",
    )
    result = list(read_pings(csv))
    assert len(result) == 1
    assert result[0].timestamp == 2000


def test_read_unknown_status_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    csv = _write_csv(
        tmp_path / "input.csv",
        "timestamp,service_id,response_time,status\n"
        "1000,svc1,50,BADVAL\n",
    )
    with caplog.at_level(logging.WARNING):
        list(read_pings(csv))
    assert any("BADVAL" in m for m in caplog.messages)


# ---------------------------------------------------------------------------
# write_intervals
# ---------------------------------------------------------------------------

SAMPLE_INTERVALS = [
    Interval("1", 1000, 2000, Status.UP),
    Interval("1", 2000, -1, Status.DOWN),
]

EXPECTED_CSV = "service_id,start_time,end_time,status\n1,1000,2000,UP\n1,2000,-1,DOWN\n"


def test_write_to_file(tmp_path: Path) -> None:
    out = tmp_path / "out.csv"
    write_intervals(SAMPLE_INTERVALS, out)
    assert out.read_text(encoding="utf-8") == EXPECTED_CSV


def test_write_atomic_no_partial_on_error(tmp_path: Path) -> None:
    existing = tmp_path / "out.csv"
    existing.write_text("original", encoding="utf-8")

    def _bad() -> list[Interval]:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        write_intervals(_bad(), existing)

    assert existing.read_text(encoding="utf-8") == "original"


def test_write_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    write_intervals(SAMPLE_INTERVALS, None)
    captured = capsys.readouterr()
    assert "service_id,start_time,end_time,status" in captured.out
    assert "1,1000,2000,UP" in captured.out
