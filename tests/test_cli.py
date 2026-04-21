import subprocess
import sys
from pathlib import Path

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
