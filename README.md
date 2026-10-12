# Fabric Medallion Platform

Metadata-driven ingestion (layered JSON config) from Azure SQL and REST APIs through Bronze → Silver → Gold, using Fabric
Lakehouses and a Warehouse. Adding a dataset = adding one small JSON file per layer under `config/`, not code. See [docs/architecture.md](docs/architecture.md).

```
Fabric-dev/
├── config/          framework_config.json · connections/ · sources/ · bronze/ · silver/ · gold/
├── docs/            architecture · metadata-model · onboarding-new-dataset · key-vault-setup
│   └── monitoring/  alert catalog + runbook      azuresql-connection-setup · scenario-small
├── lakehouse/       lh_bronze, lh_silver, lh_metadata (control tables + config)
├── warehouse/       wh_gold: control tables, gold model, load procs
├── notebooks/       api ingest · silver transform · metadata ops · maintenance
├── pipelines/       pl_medallion_daily (skeleton)
├── scripts/         deploy.py (fabric-cicd release) · sample_data/
├── src/fabric_lib/  shared logic (unit-tested)      tests/
└── .github/workflows/ci.yml
```

## Quick start
1. `py -m pip install -e .[dev]` then `py -m pytest`
2. Follow [docs/scenario-small.md](docs/scenario-small.md) to run the sample end to end in a trial workspace.
3. Onboard your own data: [docs/onboarding-new-dataset.md](docs/onboarding-new-dataset.md).

## CI/CD
Feature branch → PR (tests, GUID scan) → `main` → **dev** workspace (Git sync) → `scripts/deploy.py --env test`
→ manual approval (GitHub `prod` environment reviewers) → prod. Only dev is Git-connected; the release is idempotent.
Secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`, `FABRIC_WORKSPACE_ID_TEST`, `FABRIC_WORKSPACE_ID_PROD`.
Rollback: redeploy the previous tag; Delta `RESTORE` within retention. Assumes GitHub Actions; port if you use Azure DevOps.

## Known gaps
- `pipelines/pl_medallion_daily` is a skeleton: build in the Fabric UI, export via Git, then replace.
- `lakehouse/` and `parameter.yml` need real item definitions / ids after the first export from dev.
- Wire `mon.v_alerts` to a notification step; see [docs/monitoring/](docs/monitoring/alerts.md).
