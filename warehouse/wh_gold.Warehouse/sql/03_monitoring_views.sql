-- Monitoring views over the control metadata kept in the separate lh_metadata lakehouse.
-- Cross-database query: lh_metadata must be in the same workspace. The lakehouse SQL endpoint can lag
-- a few minutes behind Delta writes, so alerts check "stale" with a margin.
IF SCHEMA_ID('mon') IS NULL EXEC('CREATE SCHEMA mon');
GO

-- Latest run per source/layer
CREATE OR ALTER VIEW mon.v_latest_run AS
SELECT run_id, source_name, layer, status, rows_in, rows_out, rows_rejected, logged_at
FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY source_name, layer ORDER BY logged_at DESC) rn
      FROM lh_metadata.meta.run_log) x
WHERE rn = 1;
GO

-- Alert conditions: any row returned = alert. Tune SLA hours per the SDD.
CREATE OR ALTER VIEW mon.v_alerts AS
SELECT 'FAILURE' AS alert, source_name, layer, run_id, logged_at FROM mon.v_latest_run WHERE status <> 'succeeded'
UNION ALL
SELECT 'ZERO_ROWS', source_name, layer, run_id, logged_at FROM mon.v_latest_run WHERE status = 'succeeded' AND ISNULL(rows_in,0) = 0
UNION ALL
SELECT 'STALE_24H', source_name, layer, run_id, logged_at FROM mon.v_latest_run WHERE logged_at < DATEADD(HOUR,-24,SYSUTCDATETIME())
UNION ALL
SELECT 'DQ_FAIL', source_name, 'silver', run_id, logged_at FROM lh_metadata.meta.dq_result
 WHERE failed_rows > 0 AND logged_at > DATEADD(DAY,-1,SYSUTCDATETIME());
GO
