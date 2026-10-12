# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": { "name": "synapse_pyspark" }
# META }

# PARAMETERS CELL ********************

p_env = "dev"
p_source = "products_api"
p_window_start = ""      # watermark from the pipeline (ISO-8601); empty = full load
p_run_id = ""
p_kv_uri = ""            # Key Vault URI (only needed when auth != none)
p_config_root = "/lakehouse/default/Files/config"

# CELL ********************

import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pyspark.sql import functions as F

from fabric_lib.config import load_sources
from fabric_lib.bronze import paginate, audit_values

src = load_sources(p_config_root)[p_source]
base_url = src.base_url
session = requests.Session()
session.mount("https://", HTTPAdapter(max_retries=Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])))
if src.auth != "none":   # secret resolved at run time, never logged
    token = notebookutils.credentials.getSecret(p_kv_uri, src.secret_name)
    if src.auth == "bearer":
        session.headers["Authorization"] = f"Bearer {token}"
    else:
        session.headers[src.auth_header] = token

pg = src.pagination

def fetch_page(n):
    first = (n - 1) * pg["page_size"] if pg["style"] == "offset" else n
    params = {pg["page_param"]: first, pg["size_param"]: pg["page_size"]}
    if src.load_mode == "incremental" and p_window_start:
        params[src.watermark_param] = p_window_start
    r = session.get(base_url + src.source_object, params=params, timeout=60)
    r.raise_for_status()
    return r.json()

# CELL ********************

records = list(paginate(fetch_page, src.records_path))
rows_in = len(records)

target = f"lh_bronze.dbo.{src.bronze_table}"
if rows_in:
    # store raw payload as JSON string => bronze never breaks on schema drift
    df = spark.createDataFrame([(json.dumps(r),) for r in records], ["_raw"])
    a = audit_values(p_run_id, src.name)
    for k, v in a.items():
        df = df.withColumn(k, F.lit(v))
    # idempotent re-run: drop this run's rows first
    if spark.catalog.tableExists(target):
        spark.sql(f"DELETE FROM {target} WHERE _ingest_run_id = '{p_run_id}'")
    df.write.format("delta").mode("append").saveAsTable(target)

new_watermark = max((r.get(src.watermark_column) for r in records if r.get(src.watermark_column)), default=p_window_start)

# CELL ********************

notebookutils.notebook.exit(json.dumps({
    "status": "succeeded", "source": p_source, "run_id": p_run_id,
    "rows_in": rows_in, "rows_out": rows_in, "rows_rejected": 0,
    "new_watermark": new_watermark,
}))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
