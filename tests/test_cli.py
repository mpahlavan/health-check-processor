import subprocess
import sys
from pathlib import Path

from uptime.cli import _pipeline
from uptime.models import Interval, Ping, Status

DATA = Path(__file__).parent / "data"
SAMPLE_CSV = DATA / "sample_pdf.csv"
EXPECTED_CSV = DATA / "sample_pdf_expected.csv"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "uptime", *args],
        capture_output=True,
        text=True,
    )


def test_golden_output_matches_expected(tmp_path: Path) -> None:
    out = tmp_path / "out.csv"
    result = _run("--input", str(SAMPLE_CSV), "--output", str(out))
    assert result.returncode == 0
    assert out.read_text() == EXPECTED_CSV.read_text()


def test_stdout_output() -> None:
    result = _run("--input", str(SAMPLE_CSV))
    assert result.returncode == 0
    assert result.stdout == EXPECTED_CSV.read_text()


def test_missing_input_flag_exits_2() -> None:
    result = _run("--output", "out.csv")
    assert result.returncode == 2


def test_report_flag_writes_to_stderr() -> None:
    result = _run("--input", str(SAMPLE_CSV), "--report")
    assert result.returncode == 0
    assert "Uptime Report" in result.stderr
    assert "Service" in result.stderr


# ---------------------------------------------------------------------------
# Unit tests for pipeline (boost coverage without subprocess)
# ---------------------------------------------------------------------------


def test_pipeline_sorts_by_service_then_start_time() -> None:
    pings = [
        Ping(2000, "b", Status.UP),
        Ping(1000, "a", Status.DOWN),
        Ping(3000, "a", Status.UP),
    ]
    result = _pipeline(pings)
    assert result[0].service_id == "a"
    assert result[0].start_time == 1000
    assert result[1].service_id == "a"
    assert result[-1].service_id == "b"


def test_pipeline_empty_input() -> None:
    assert _pipeline([]) == []


def test_pipeline_resolves_unknown() -> None:
    pings = [
        Ping(1000, "svc", Status.UNKNOWN),
        Ping(2000, "svc", Status.UP),
    ]
    result = _pipeline(pings)
    assert result == [Interval("svc", 1000, -1, Status.UP)]
