# Onboarding a new dataset

Add one file per layer under `config/`, named after the `dataset_id`.

1. **Connection** – if new: create it in Fabric (`azuresql-connection-setup.md`, `key-vault-setup.md`) and add `config/connections/<name>.json` (references only; for bearer/api-key set `auth` + `secret_name`).
2. **Source** – `config/sources/<dataset_id>.json`: copy `orders_sql` (SQL, put the query next to the table) or `products_api` (REST: endpoint, pagination, records_path).
3. **Bronze** – `config/bronze/<dataset_id>.json`: target table, `write_mode`.
4. **Silver** – `config/silver/<dataset_id>.json`: `business_key`, `dedupe_order_column`, `required_columns` (contract), `dq` rules.
5. **Gold** – if analysts need it: add the table/procedure in `warehouse/.../sql/` and `config/gold/<target>.json` with `depends_on_silver` / `depends_on_gold`.
6. **Test** – `py -m pytest` checks all cross-file links, procedures, load order and secrets. Then in dev run bronze → silver → gold twice on one window; counts must match.
7. **Release** – upload `config/` to the lakehouse `Files/config/` (dev), open a PR; CI promotes to test/prod. Use `"enabled": false` in the source file to merge config before the source is ready.
