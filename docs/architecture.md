# Architecture

Metadata-driven medallion on Microsoft Fabric. New datasets are onboarded by adding config, not code.

```
 Azure SQL ──Copy activity──┐
                            ├─► lh_bronze (raw Delta, append, audit cols)
 REST API ──Notebook────────┘          │ nb_silver_transform
                                       ▼ (schema contract (required_columns), dedupe, DQ, MERGE on business key)
                                  lh_silver (clean Delta)
                                       │ stored procs (cross-database query)
                                       ▼
                               wh_gold (star schema) ─► Power BI
 Control metadata in lh_metadata (Delta, schema meta): watermark, run_log, dq_result  + the config/ JSON files
 Orchestration: pl_medallion_daily (ForEach over enabled `config/sources/*`, then gold in `depends_on_gold` order)
```

| Layer | Item | Store | Write pattern |
|---|---|---|---|
| Bronze | `lh_bronze` | Lakehouse | append + `_ingest_run_id` (re-run safe) |
| Silver | `lh_silver` | Lakehouse | Delta MERGE on business key |
| Gold | `wh_gold` | Warehouse | idempotent T-SQL procedures |
| Metadata | `lh_metadata` | Lakehouse | watermark (MERGE, forward-only), run_log / dq_result (append), `Files/config/` |

## Repo map
| Path | Purpose |
|---|---|
| `config/` | layered metadata: `framework_config.json` (global), `connections/`, `sources/`, `bronze/`, `silver/`, `gold/` (see `metadata-model.md`). Secrets stay out; only Key Vault secret names |
| `src/fabric_lib/` + `tests/` | shared logic, unit-tested with pytest outside Fabric |
| `notebooks/`, `pipelines/`, `lakehouse/`, `warehouse/` | Fabric items (Git format) |
| `scripts/` | release script (`deploy.py`), sample source data |
| `docs/` | this documentation; `docs/monitoring/` alert catalog + runbook |

## Principles
- Idempotent at every layer; the watermark advances only after gold succeeds.
- No secrets or GUIDs in the repo; Key Vault + per-environment parameters.
- Only dev is Git-connected; test/prod via `scripts/deploy.py` (fabric-cicd).
