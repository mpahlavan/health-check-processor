# Algorithm Walkthrough

## State Machine Overview

Each service's ping stream passes through two pure functions:

```
raw pings (unsorted, interleaved)
    │
    ▼
sort by (service_id, timestamp)
    │
    ▼
group by service_id
    │
    ├─► resolve_unknowns      # ? → UP or DOWN (or drop)
    │
    └─► collapse_to_intervals # consecutive same-status → one interval
```

The status transitions the spec defines:

```
     ┌──────┐   UP    ┌──────┐
     │  UP  │────────►│  UP  │  (same — extend current interval)
     └──────┘         └──────┘
         │   DOWN  ┌──────┐
         └────────►│ DOWN │
                   └──────┘
                       │
          ?    ┌───────┴───────┐
        ──────►│    UNKNOWN    │──► next UP  → becomes UP
               └───────────────┘──► next DOWN → becomes DOWN
                                ──► no successor → dropped
```

---

## `resolve_unknowns` — Forward-Fill

### How it works

Buffer consecutive `UNKNOWN` pings. When the next definitive ping
(`UP` or `DOWN`) arrives, re-emit all buffered pings with that status,
then emit the definitive ping itself. If the stream ends while the buffer
is non-empty, discard it — those are trailing UNKNOWNs with no resolution.

### Worked example

Input (one service, sorted by timestamp):

| timestamp | status  |
|-----------|---------|
| 1000      | UNKNOWN |
| 2000      | UNKNOWN |
| 3000      | DOWN    |
| 4000      | UP      |

Processing step by step:

1. `t=1000 UNKNOWN` → buffer: `[1000?]`
2. `t=2000 UNKNOWN` → buffer: `[1000?, 2000?]`
3. `t=3000 DOWN` → flush buffer with DOWN, then emit DOWN
   - emit `1000 DOWN`, `2000 DOWN`, `3000 DOWN`
   - buffer: `[]`
4. `t=4000 UP` → emit directly: `4000 UP`

Output:

| timestamp | status |
|-----------|--------|
| 1000      | DOWN   |
| 2000      | DOWN   |
| 3000      | DOWN   |
| 4000      | UP     |

### Why not resolve trailing UNKNOWNs to DOWN?

The spec defines resolution as: *"UNKNOWN followed by X → X"*.
A trailing UNKNOWN has no X — the rule cannot be applied.
Resolving it to DOWN would be a conservative guess, not a derivation.
See ADR-001 in [DECISIONS.md](DECISIONS.md) for the full trade-off.

---

## `collapse_to_intervals` — Transition Detection

### How it works

Walk the resolved ping stream tracking `(current_status, start_time)`.
On every status change, close the current interval and open a new one.
After the loop, close the final interval with `end_time = -1` (open).

### Worked example

Input (after `resolve_unknowns`):

| timestamp | status |
|-----------|--------|
| 1000      | DOWN   |
| 2000      | DOWN   |
| 3000      | DOWN   |
| 4000      | UP     |

Processing:

| event        | action                                      | interval emitted               |
|--------------|---------------------------------------------|--------------------------------|
| `1000 DOWN`  | open interval: status=DOWN, start=1000      | —                              |
| `2000 DOWN`  | same status — do nothing                    | —                              |
| `3000 DOWN`  | same status — do nothing                    | —                              |
| `4000 UP`    | status change → close DOWN, open UP         | `[1000, 4000) DOWN`            |
| end of stream| close final interval with end_time=-1       | `[4000, -1) UP`                |

Output intervals:

| start | end  | status |
|-------|------|--------|
| 1000  | 4000 | DOWN   |
| 4000  | -1   | UP     |

The transition timestamp (`4000`) is simultaneously the `end_time` of the
closing interval and the `start_time` of the new one — intervals are
contiguous with no gaps.

---

## Time and Space Complexity

| Step                    | Time        | Space                        |
|-------------------------|-------------|------------------------------|
| Sort per service        | O(n log n)  | O(n) — full service buffer   |
| `resolve_unknowns`      | O(n)        | O(k) — k = pending UNKNOWNs |
| `collapse_to_intervals` | O(n)        | O(1) — two variables         |
| **Total**               | **O(n log n)** | **O(n) per service**      |

Where `n` = number of pings for a single service.

The sort dominates. The two processing passes are linear and streaming —
they hold at most one ping in flight at any moment. Memory is bounded by
the largest single-service ping count, not the total file size.
