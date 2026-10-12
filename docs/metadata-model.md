# Metadata model: one JSON per concern, per layer

Metadata-driven: same notebooks and pipelines for every dataset; behaviour comes from `config/`.
Splitting by layer keeps diffs small, lets different owners review their own layer, and makes each file validate against one concern.

```
config/
├── framework_config.json      global settings only (layers, control tables, retention, alert thresholds, Key Vault refs per env)
├── connections/<name>.json    how to reach a system
├── sources/<dataset_id>.json  what to extract (sql{} or rest{})
├── bronze/<dataset_id>.json   how raw data lands
├── silver/<dataset_id>.json   keys, dedupe, DQ, schema contract
└── gold/<target>.json         warehouse table, load procedure, dependencies
```
`sources/`, `bronze/` and `silver/` are keyed by `dataset_id` (file name = id). `gold/` is keyed by target table because a fact usually combines several datasets.

| File | Fields |
|---|---|
| `connections/` | `name`, `type`, `auth` (`none`\|`bearer`\|`api_key`\|`service_principal`), `base_url` (REST) or `server_ref`/`database_ref` (SQL), `secret_name(s)` = Key Vault secret **names** |
| `sources/` | `dataset_id`, `source_type` (`sql`\|`rest`), `enabled`, `connection`, `sql{table, query, load_mode, watermark_column}` or `rest{endpoint, load_mode, watermark_column, watermark_param, pagination{}, records_path}`, `additional_config{}` |
| `bronze/` | `table`, `write_mode` (append), `partition_by[]`, `keep_raw_payload` |
| `silver/` | `table`, `write_mode` (merge), `business_key[]`, `dedupe_order_column`, `required_columns{}` (schema contract), `dq{not_null[], unique[]}` |
| `gold/` | `target`, `procedure`, `load_type` (`upsert`\|`full_refresh`), `depends_on_silver[]`, `depends_on_gold[]`, `enabled` |

SQL `query` supports `{watermark}` and `{window_end}` placeholders filled by the pipeline.
Secrets never appear in these files, only Key Vault secret names.

## What is validated (`py -m pytest`)
- field values (load mode, auth, pagination, watermark, business key); every REST source inherits base URL/auth from its connection
- every source has matching bronze and silver files; no orphan layer files; the referenced connection exists
- each gold file references real silver datasets and a procedure that exists in `warehouse/**/*.sql`
- gold dependencies have a valid load order (dimensions before facts) with no cycles
- no password/token-like keys or `user:pass@host` strings in any config file

## Control tables: separate `lh_metadata` lakehouse (schema `meta`)
Kept apart from the data layers so metadata has its own lifecycle, access and maintenance, and survives a data rebuild. The `config/` JSON files are uploaded to its `Files/config/`.

| Table | Columns | Write pattern |
|---|---|---|
| `meta.watermark` | source_name, watermark_value, updated_at | MERGE, forward-only (`advance_watermark`) |
| `meta.run_log` | run_id, source_name, layer, status, rows_in/out/rejected, logged_at | append |
| `meta.dq_result` | run_id, source_name, check_name, failed_rows, logged_at | append |

All access goes through `notebooks/nb_metadata_ops` (actions: `init`, `get_watermark`, `commit_watermark`, `log_run`, `log_dq`). Table names come from `framework_config.json` → `control`. The warehouse reads them through views in `mon.*` (cross-database query).
