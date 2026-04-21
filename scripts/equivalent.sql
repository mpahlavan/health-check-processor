-- DuckDB equivalent of the uptime interval processor
--
-- Reproduces the same output as:
--   uv run uptime --input data/scilifelab-data-centre-coding-test-input.csv
--
-- Run with:
--   duckdb -c ".read scripts/equivalent.sql"
-- Or interactively:
--   duckdb
--   .read scripts/equivalent.sql

-- Step 1: load raw pings, resolve UNKNOWN via forward-fill
WITH raw AS (
    SELECT
        CAST(timestamp    AS BIGINT) AS timestamp,
        CAST(service_id   AS VARCHAR) AS service_id,
        status
    FROM read_csv_auto(
        'data/scilifelab-data-centre-coding-test-input.csv',
        header = true
    )
    WHERE status IN ('UP', 'DOWN', 'UNKNOWN')
),

-- Step 2: forward-fill UNKNOWN with the next definitive status per service
--         IGNORE NULLS skips UNKNOWN rows when looking for the next value
filled AS (
    SELECT
        timestamp,
        service_id,
        COALESCE(
            CASE WHEN status != 'UNKNOWN' THEN status END,
            LEAD(CASE WHEN status != 'UNKNOWN' THEN status END)
                IGNORE NULLS
                OVER (PARTITION BY service_id ORDER BY timestamp)
        ) AS status
    FROM raw
),

-- Step 3: drop trailing UNKNOWNs (rows where forward-fill found no successor)
resolved AS (
    SELECT timestamp, service_id, status
    FROM filled
    WHERE status IS NOT NULL
),

-- Step 4: detect transitions — mark the start of each new interval
transitions AS (
    SELECT
        timestamp,
        service_id,
        status,
        LAG(status) OVER (PARTITION BY service_id ORDER BY timestamp) AS prev_status
    FROM resolved
),

-- Step 5: assign an interval group number to consecutive same-status runs
groups AS (
    SELECT
        timestamp,
        service_id,
        status,
        SUM(CASE WHEN status != COALESCE(prev_status, '') THEN 1 ELSE 0 END)
            OVER (PARTITION BY service_id ORDER BY timestamp) AS grp
    FROM transitions
),

-- Step 6: collapse each group into one interval
intervals AS (
    SELECT
        service_id,
        MIN(timestamp) AS start_time,
        MAX(timestamp) AS end_time,
        ANY_VALUE(status) AS status
    FROM groups
    GROUP BY service_id, grp
),

-- Step 7: set end_time = -1 for the last interval per service
final AS (
    SELECT
        service_id,
        start_time,
        CASE
            WHEN end_time = MAX(end_time) OVER (PARTITION BY service_id)
            THEN -1
            ELSE LEAD(start_time) OVER (PARTITION BY service_id ORDER BY start_time)
        END AS end_time,
        status
    FROM intervals
)

SELECT service_id, start_time, end_time, status
FROM final
ORDER BY service_id, start_time;
