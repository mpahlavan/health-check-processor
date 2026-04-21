# Uptime Interval Processor

Converts a CSV of raw monitoring pings into a clean CSV of per-service
uptime intervals. Built as a submission for the SciLifeLab Data Centre
Python Software Developer coding test.

---

## Problem

A monitoring system emits one row per ping:

```
timestamp,service_id,response_time,status
1767951572,1,72,UP
1767558032,1,0,DOWN
1767340434,2,0,UNKNOWN
```

The goal is to collapse these into contiguous status intervals per service:

```
service_id,start_time,end_time,status
1,1767400524,1767558032,UP
1,1767558032,1767951572,DOWN
1,1767951572,-1,UP
2,1766478924,-1,UP
```

Rules:
- `UNKNOWN` inherits the **next** definitive status (`UP` or `DOWN`)
- Trailing `UNKNOWN` with no successor is **dropped** (see [DECISIONS.md](DECISIONS.md))
- The final open interval uses `end_time = -1`
- Output is sorted by `service_id`, then `start_time`

---

## Quickstart

```bash
# install
uv sync

# run on the provided input
uv run uptime --input data/scilifelab-data-centre-coding-test-input.csv \
              --output data/out.csv \
              --report

# or via make
make run
```

**`--report`** prints a per-service uptime summary to stderr:

```
=== Uptime Report ===
Service 1:  90.7% UP  |  outages: 400  |  longest outage: 8h 52m
Service 2: 100.0% UP  |  outages: 0
```

---

## Docker

```bash
# build
docker build -t uptime .

# run
docker run --rm -v $(pwd)/data:/data uptime \
  --input /data/scilifelab-data-centre-coding-test-input.csv \
  --output /data/out.csv
```

---

## Development

```bash
make install   # uv sync
make test      # pytest with coverage
make lint      # ruff check + format
make type      # mypy --strict
make check     # all of the above
```

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/)

---

## Algorithm

Two pure functions process each service's pings in sequence:

1. **`resolve_unknowns`** — forward-fills `UNKNOWN` pings with the next
   definitive status. Trailing `UNKNOWN`s with no successor are dropped.
2. **`collapse_to_intervals`** — detects status transitions and emits
   half-open intervals `[start, end)`. The last interval per service gets
   `end_time = -1`.

Both operate on iterators — memory usage is bounded by the largest
single-service ping count, not the total file size.

Full walkthrough: [ALGORITHM.md](ALGORITHM.md)

---

## Design Decisions

Key non-obvious choices — trailing UNKNOWN handling, sort order, service_id
as string, atomic file writes — are documented with trade-offs in
[DECISIONS.md](DECISIONS.md).

---

## Project Structure

```
src/uptime/
├── models.py      # Ping, Interval dataclasses; Status enum
├── intervals.py   # core logic: resolve_unknowns, collapse_to_intervals
├── io.py          # streaming CSV reader/writer
├── cli.py         # argparse entry point
└── metrics.py     # uptime %, outage counts, longest outage

tests/
├── test_intervals.py   # golden test + edge cases
├── test_properties.py  # Hypothesis property tests
├── test_io.py          # CSV read/write tests
└── test_cli.py         # end-to-end CLI tests
```

---

## Assumptions

- Input timestamps are Unix epoch seconds (integers)
- `service_id` is treated as an opaque string — sort is lexicographic
- Per-service ping count fits in memory for sorting
- No incremental mode — full recompute on every run
- No web UI, no database, no cloud dependencies
