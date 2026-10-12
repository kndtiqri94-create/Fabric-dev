# Azure SQL / SQL MI connection setup

Checklist
- [ ] Network: Azure SQL firewall allows Fabric, or use a managed private endpoint / VNet data gateway. SQL MI usually needs the VNet data gateway or a public endpoint (3342) with NSG rules.
- [ ] Create a least-privilege login: `CREATE USER [fabric_reader] ...; ALTER ROLE db_datareader ADD MEMBER [fabric_reader];` (read-only).
- [ ] In Fabric: Manage connections → New → Azure SQL Database; name it exactly as the `connection` in `config/sources/*.json` (`conn_sales_azuresql`).
- [ ] Auth: service principal (secret in Key Vault) or workspace identity. Avoid personal accounts.
- [ ] Seed sample data with `scripts/sample_data/azure_sql_seed.sql`.
- [ ] Test: Copy activity preview on `dbo.Orders` returns rows; incremental query `WHERE ModifiedDate > @watermark` works.
- [ ] Index `ModifiedDate` on large tables so incremental pulls stay cheap.
