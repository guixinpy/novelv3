# Trace Anomaly Long-Run Samples Dogfood

## Runtime

- Date: 2026-06-04
- Source database: `data/agent_native_dogfood_20260526.db`
- Read mode: SQLite immutable read-only URI
- Purpose: prove the Trace anomaly long-run sample projection has real
  Writing Agent run/step samples from an API-backed dogfood loop, not only
  synthetic unit-test windows.

The database remains ignored under `data/`; this note records the stable
read-only query evidence used by `inspect_agent_dogfood_evidence`.

## Queries

```powershell
sqlite3 "file:data/agent_native_dogfood_20260526.db?mode=ro&immutable=1" `
  "select count(*) from writing_agent_runs;
   select count(*) from writing_agent_steps;
   select status, count(*) from writing_agent_runs group by status order by status;
   select entrypoint, count(*) from writing_agent_runs group by entrypoint order by entrypoint;"
```

Output:

```text
14
31
blocked|2
success|12
chapter_generate|2
dogfood|12
```

```powershell
sqlite3 "file:data/agent_native_dogfood_20260526.db?mode=ro&immutable=1" `
  "select chapter_index, count(*) from writing_agent_steps
   where chapter_index is not null
   group by chapter_index
   order by chapter_index;"
```

Output:

```text
1|1
2|10
3|4
```

```powershell
sqlite3 "file:data/agent_native_dogfood_20260526.db?mode=ro&immutable=1" `
  "select r.entrypoint, r.status, count(distinct r.id), count(s.id)
   from writing_agent_runs r
   join writing_agent_steps s on s.run_id=r.id
   group by r.entrypoint,r.status
   order by r.entrypoint,r.status;"
```

Output:

```text
chapter_generate|success|2|2
dogfood|blocked|2|2
dogfood|success|10|27
```

## Evidence Summary

- Real run count: 14
- Real step count: 31
- Dogfood entrypoint run count: 12
- Success run count: 12
- Blocked run count: 2
- Covered chapters: 1, 2, 3

This closes the previous Trace anomaly threshold calibration residue
`trace_anomaly_threshold_long_run_sample_execution`: there is now a recorded
long-run dogfood sample window that can be reviewed by
`inspect_agent_trace_anomaly_long_run_samples` and then by
`inspect_agent_trace_anomaly_threshold_review`.
