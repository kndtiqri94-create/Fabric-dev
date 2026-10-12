# Runbook: pl_medallion_daily
Owner: data-eng · Schedule: daily · Expected duration: ~30 min

**Symptom: pipeline failed alert**
1. Monitor hub → run → find the failed activity; note `p_source`, `run_id`, window.
2. Bronze fail: check connection/gateway or API token (Key Vault); source reachable?
3. Silver fail: read notebook exit value/error; check schema drift in bronze.
4. Gold fail: check warehouse proc error; silver table present?

**Safe re-run:** re-trigger with the same `p_source` and window. Bronze deletes its own `run_id` rows, silver MERGE and gold procs are idempotent, and the watermark only advances after gold succeeds, so a re-run yields identical results.

**Rollback data:** Delta `RESTORE TABLE ... TO VERSION AS OF n` within VACUUM retention (≥168h); redeploy previous git tag for code.

**Escalate:** platform team if capacity throttled or workspace unavailable.
