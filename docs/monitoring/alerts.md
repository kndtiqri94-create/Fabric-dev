# Alert catalog
Source: `SELECT * FROM mon.v_alerts` (wh_gold, reads `lh_metadata.meta.*`), checked by a scheduled pipeline after the daily load → Teams/email. Payloads carry ids and counts only.

| Alert | Condition | Severity | Owner channel | First action |
|---|---|---|---|---|
| FAILURE | latest run status ≠ succeeded | High | data-eng | Open Monitor hub run by `run_id`; read error; see runbook |
| ZERO_ROWS | succeeded but rows_in = 0 | Medium | data-eng | Check source watermark/window; source may be genuinely quiet |
| STALE_24H | no run logged in 24h | High | data-eng | Check schedule/trigger and capacity (paused/throttled?) |
| DQ_FAIL | failed_rows > 0 in last day | Medium | data-owner | Inspect `lh_metadata.meta.dq_result`, trace to source defect |
| CAPACITY | throttling in Capacity Metrics app | High | platform | Review peaks, reschedule/scale SKU |

Tune the 24h SLA to the SDD. Verify Data Activator / Teams activity availability in your tenant.
