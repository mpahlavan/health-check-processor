import csv
import logging
import sys
import tempfile
from collections.abc import Iterable, Iterator
from pathlib import Path

from .models import Interval, Ping, Status

logger = logging.getLogger(__name__)

_REQUIRED_COLUMNS = {"timestamp", "service_id", "response_time", "status"}


def read_pings(path: Path) -> Iterator[Ping]:
    """Streaming CSV reader — memory-bounded regardless of file size.

    Yields one Ping at a time; the file is never fully loaded into memory.

    Exits with code 2 on:
      - empty file (no header)
      - missing or renamed columns
      - non-UTF-8 bytes

    Logs a warning and skips rows with:
      - unrecognised status value
      - non-integer timestamp
    """
    try:
        fh = path.open(newline="", encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot open {path}: {exc}", file=sys.stderr)
        sys.exit(2)

    with fh:
        reader = csv.DictReader(fh)

        # --- header validation ---
        try:
            fieldnames = reader.fieldnames  # reads the first line
        except UnicodeDecodeError as exc:
            print(f"error: non-UTF-8 bytes in header: {exc}", file=sys.stderr)
            sys.exit(2)

        if not fieldnames:
            print(f"error: {path} is empty", file=sys.stderr)
            sys.exit(2)

        missing = _REQUIRED_COLUMNS - set(fieldnames)
        if missing:
            print(f"error: missing columns: {sorted(missing)}", file=sys.stderr)
            sys.exit(2)

        # --- row streaming (O(1) memory — one row at a time) ---
        rejected = 0
        lineno = 1

        for row in reader:
            lineno += 1

            # non-UTF-8 mid-file: Python raises on this line during decode
            raw_status = str(row["status"]).strip()
            try:
                status = Status(raw_status)
            except ValueError:
                logger.warning("line %d: unknown status %r — skipping", lineno, raw_status)
                rejected += 1
                continue

            raw_ts = str(row["timestamp"]).strip()
            try:
                timestamp = int(raw_ts)
            except ValueError:
                logger.warning("line %d: invalid timestamp %r — skipping", lineno, raw_ts)
                rejected += 1
                continue

            yield Ping(
                timestamp=timestamp,
                service_id=str(row["service_id"]).strip(),
                status=status,
            )

        if rejected:
            logger.warning("skipped %d malformed row(s) in %s", rejected, path)


def write_intervals(intervals: Iterable[Interval], path: Path | None) -> None:
    """Write intervals as CSV to a file or stdout.

    File output uses an atomic tmp-then-rename so an interrupted run
    never leaves a partial output file.
    """
    header = ["service_id", "start_time", "end_time", "status"]

    def _write(writer: "csv.writer") -> None:  # type: ignore[type-arg]
        writer.writerow(header)
        for interval in intervals:
            writer.writerow(
                [
                    interval.service_id,
                    interval.start_time,
                    interval.end_time,
                    interval.status.value,
                ]
            )

    if path is None:
        _write(csv.writer(sys.stdout))
        return

    tmp_fd, tmp_str = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    tmp_path = Path(tmp_str)
    try:
        with open(tmp_fd, "w", newline="", encoding="utf-8") as fh:
            _write(csv.writer(fh))
        tmp_path.replace(path)  # atomic on POSIX; best-effort on Windows
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
