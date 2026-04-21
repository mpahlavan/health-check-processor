# Architecture Decision Records

---

## ADR-001: Trailing UNKNOWN Handling

**Status:** Accepted

### Context

The spec states: *"UNKNOWN followed by UP → treat as UP; UNKNOWN followed
by DOWN → treat as DOWN."* Resolution requires a *following* definitive
status. A trailing UNKNOWN at the end of a service's stream has no
successor.

Example:

```
timestamp  status
1000       UP
2000       UNKNOWN   ← no ping follows for this service
```

### Options

**Option A — Resolve to DOWN (conservative)**
- Assume "no news is bad news": treat unresolved UNKNOWN as an outage.
- Pros: never silently ignores a potential failure.
- Cons: invents a status the data does not support; violates the
  forward-fill rule which requires a successor.

**Option B — Drop entirely (strict spec adherence)**
- If resolution is undefined, produce no output for that ping.
- Pros: output only contains statuses derivable from the data.
- Cons: a real failure at end-of-stream is invisible in the output.

### Decision

**Drop** (Option B).

The spec defines output `status ∈ {UP, DOWN}`. The resolution rule
requires a following definitive status — applying it without one would
be an extrapolation, not a derivation. Dropping is the only
spec-compliant choice. The behaviour is logged as a warning so operators
can detect services whose last known state is unresolved.

---

## ADR-002: `service_id` as String

**Status:** Accepted

### Context

The input column description says "integer", but the output column
description says "string". Services `1` and `10` both appear in the
data.

### Decision

Treat `service_id` as an **opaque string** throughout.

- No cast to `int` at read time — preserves leading zeros if they exist.
- Sort order is **lexicographic**: `"10"` sorts before `"2"`.
- Known deviation: if numeric sort is required, an explicit `int` cast
  at sort time is the one-line extension point.

---

## ADR-003: In-Memory Sort Per Service

**Status:** Accepted

### Context

Pings arrive interleaved across services. Processing requires per-service
sorted order. The sort must buffer all pings for one service before emitting
any intervals for that service.

### Decision

Sort per-service in memory using Python's built-in `sorted()`.

- Assumption: per-service ping count fits comfortably in RAM.
  At ~100 bytes per `Ping` object, 100 000 pings ≈ 10 MB — well within
  any reasonable limit.
- For inputs where a single service has >10 M pings, the natural
  extension is an external sort (chunk → sort chunks → `heapq.merge`).
  The iterator-based design of `collapse_to_intervals` already supports
  this without modification.

---

## ADR-004: Atomic File Output

**Status:** Accepted

### Context

Writing directly to the output path risks leaving a partial file if the
process is interrupted mid-write (OOM, SIGKILL, disk full).

### Decision

Use a **write-to-temp-then-rename** strategy:

1. Open a sibling `.tmp` file in the same directory (same filesystem).
2. Write all output.
3. `Path.replace()` — atomic on POSIX; best-effort on Windows.
4. On any exception, delete the `.tmp` file and re-raise.

The previous output file is never touched until the new one is complete.
Re-running after a failed write is always safe.

---

## ADR-005: stdlib Only — No pandas or numpy

**Status:** Accepted

### Context

The problem is a sort + two linear scans over a CSV. No matrix
operations, no dataframe joins, no numerical computation.

### Decision

Core logic uses **Python stdlib only** (`csv`, `dataclasses`, `argparse`,
`itertools`, `pathlib`, `logging`).

- Zero install-time risk from third-party dependencies.
- The `dependencies = []` line in `pyproject.toml` is intentional and
  is itself a design statement.
- For inputs beyond ~10 M rows, Polars (lazy, multi-threaded) is the
  natural upgrade path — the streaming iterator design makes the
  swap a one-module replacement, not a rewrite.
