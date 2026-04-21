# Architecture

## Current Design

The tool is a stateless batch processor: read all pings, sort per service,
run the state machine, write intervals. No daemon, no database, no network.

```
stdin/file ──► read_pings ──► _pipeline ──► write_intervals ──► stdout/file
                                  │
                          ┌───────┴────────┐
                    resolve_unknowns  collapse_to_intervals
```

The two core functions are pure and iterator-based — they hold O(1) state
per ping and can process an arbitrarily long stream. The only buffering
is the per-service sort, which is bounded by the largest single-service
ping count (see DECISIONS.md ADR-003).

---

## Scaling Path

The current dataset is 4.6 MB / ~236k rows, processed in under 1 second
on a laptop. Nothing exotic is required. The scaling notes below describe
what would change if the dataset grew 100–1000×.

### Horizontal scaling (embarrassingly parallel)

The algorithm is independent per `service_id` — no cross-service state.
The natural parallelisation:

1. Shard input by `hash(service_id) % N` into N partitions.
2. Run the full pipeline on each shard independently (threads, processes,
   k8s pods, or Slurm array jobs).
3. Concatenate and sort the N output files — no cross-shard merge logic
   required.

For SciLifeLab infrastructure running on **NAISS** (the Swedish national
academic HPC network), a Slurm array job is the natural fit:

```bash
# array.sbatch sketch — one task per service shard
#SBATCH --array=0-15
shard=$SLURM_ARRAY_TASK_ID
uptime --input data/shard_${shard}.csv --output out/shard_${shard}.csv
```

Each task is stateless and restartable — a failed task reruns without
affecting others.

### Vertical scaling (single-node speedups)

- **Polars** (lazy, multi-threaded): the `resolve_unknowns` +
  `collapse_to_intervals` logic maps to a `group_by` + `sort` +
  window-function pipeline. On this hardware Polars reads CSV ~20×
  faster than `csv.DictReader` and sorts multi-threaded. Worthwhile
  above ~50 M rows.
- **DuckDB**: the same logic in SQL using `LAG`/`LEAD` window functions
  over a `GROUP BY service_id ORDER BY timestamp` partition. DuckDB's
  out-of-core operators handle datasets larger than RAM with no code
  changes. A complete working equivalent is in
  [`scripts/equivalent.sql`](scripts/equivalent.sql).
- **PyArrow**: memory-mapped Parquet reads leverage the OS page cache —
  important on parallel file systems (Lustre, GPFS, BeeGFS) where
  many-small-file patterns saturate the metadata server.

### Storage format

For large-scale production use, replacing CSV with **Parquet** gives:

- 5–10× compression (columnar + dictionary encoding for `status`).
- Projection pushdown: `response_time` is never needed in the output —
  Parquet readers skip it entirely.
- Time-partitioned layout (`/pings/year=2026/month=04/`) enables
  incremental processing and predicate pushdown.

The PDF notes that pings are "recorded in a relational database" — at
source, the computation can be pushed into the DB as a window function
query, avoiding the CSV export entirely.

### GPU — honest framing

This workload is a sort + two linear scans. It is I/O-bound and
branch-bound, not arithmetic-bound. GPU acceleration (cuDF) would add
PCIe transfer overhead without compute benefit for datasets below ~100 GB.
Calling this out is more useful than claiming GPU relevance where none
exists.

---

## FAIR Data Principles

The output is designed to be machine-interpretable and reproducible:

- **Findable**: stable column names, typed schema (`service_id` string,
  timestamps integers, `status` enum), deterministic sort order.
- **Accessible**: plain CSV — no proprietary format, no authentication
  required to read the output.
- **Interoperable**: RFC 4180 CSV with UTF-8 encoding; `end_time = -1`
  is explicitly documented rather than left implicit.
- **Reusable**: same input always produces byte-identical output (atomic
  write, stable sort). Pinned dependencies (`uv.lock`) and a Docker image
  ensure the computation is reproducible across environments and time.

Schema fingerprinting (hashing the input column names on every run) is
a natural next step for long-running pipelines where upstream schema
drift is a risk.
