# Scenario: small sales platform (the sample)

Sources: Azure SQL (`orders_sql`, `customers_sql`) and the public no-auth `products_api` (dummyjson.com).
Target: `gold.dim_customer`, `gold.dim_product`, `gold.fact_orders`.

Walkthrough (trial workspace)
1. Create `lh_bronze`, `lh_silver`, `lh_metadata` (all schema-enabled) and `wh_gold`; run `warehouse/.../sql/01-03` in order, then run `nb_metadata_ops` with `p_action=init` to create the control tables.
2. Run `scripts/sample_data/azure_sql_seed.sql` on your Azure SQL; create the two connections.
3. Upload the `config/` folder to `lh_metadata` → `Files/config/` (attach `lh_metadata` as the default lakehouse of the orchestration notebooks); attach `fabric_lib` via a Fabric Environment.
4. Bronze: Copy activity for the two SQL tables; run `nb_bronze_api_ingest` with `p_source=products_api`.
5. Silver: run `nb_silver_transform` per dataset with the same `p_run_id`.
6. Gold: `EXEC gold.usp_load_dim_customer; EXEC gold.usp_load_dim_product; EXEC gold.usp_load_fact_orders;`
7. Verify: `SELECT COUNT(*)` per gold table (3 customers, 30 products, 4 orders), then update an order in source and re-run to see only the delta move.
