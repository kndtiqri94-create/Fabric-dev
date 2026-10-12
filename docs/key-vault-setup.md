# Key Vault setup

One vault per environment (dev/test/prod); URIs are referenced in `framework_config.json` (`key_vault_uri_ref`) and supplied to notebooks as `p_kv_uri` from the pipeline / variable library, never hard-coded.

| Secret name | Used by |
|---|---|
| `secret_name` in `config/connections/<name>.json` (e.g. `conn_crm_api-token`) | API connections with `auth: bearer` / `api_key` (read by `nb_bronze_api_ingest`) |
| `sales-sql-principal-id`, `sales-sql-principal-key` | Azure SQL service principal (Fabric connection) |

Steps
1. Create the vault (RBAC mode); grant the Fabric workspace identity **Key Vault Secrets User**.
2. Add secrets with the names above.
3. In notebooks, read only via `notebookutils.credentials.getSecret(kv_uri, name)`. Never print or log the value.
4. Rotate by adding a new secret version; no code change needed.
