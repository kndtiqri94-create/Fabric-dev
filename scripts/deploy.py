"""Scripted release using the fabric-cicd library. Idempotent: re-running converges.

Usage: python scripts/deploy.py --env test
Env vars (from the CI secret store, never the repo):
  FABRIC_WORKSPACE_ID_<ENV>   target workspace id
  AZURE_CLIENT_ID / AZURE_TENANT_ID / AZURE_CLIENT_SECRET   service principal
"""
import argparse
import os
import sys
from pathlib import Path

from azure.identity import ClientSecretCredential
from fabric_cicd import FabricWorkspace, publish_all_items, unpublish_all_orphan_items

ROOT = Path(__file__).resolve().parent.parent
ITEM_TYPES = ["Lakehouse", "Notebook", "DataPipeline", "Warehouse", "Environment"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", required=True, choices=["dev", "test", "prod"])
    args = ap.parse_args()

    ws_var = f"FABRIC_WORKSPACE_ID_{args.env.upper()}"
    missing = [v for v in (ws_var, "AZURE_CLIENT_ID", "AZURE_TENANT_ID", "AZURE_CLIENT_SECRET") if not os.environ.get(v)]
    if missing:  # release fails when a mapping is missing
        print(f"Missing required env vars: {', '.join(missing)}")
        return 1

    cred = ClientSecretCredential(os.environ["AZURE_TENANT_ID"], os.environ["AZURE_CLIENT_ID"], os.environ["AZURE_CLIENT_SECRET"])
    ws = FabricWorkspace(
        workspace_id=os.environ[ws_var],
        environment=args.env,
        repository_directory=str(ROOT),
        item_type_in_scope=ITEM_TYPES,
        token_credential=cred,
    )
    publish_all_items(ws)
    unpublish_all_orphan_items(ws)
    return 0


if __name__ == "__main__":
    sys.exit(main())
