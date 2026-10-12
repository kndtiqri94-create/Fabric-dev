# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": { "name": "synapse_pyspark" }
# META }

# PARAMETERS CELL ********************

p_env = "dev"
p_source = "orders_sql"
p_run_id = ""
p_config_root = "/lakehouse/default/Files/config"

# CELL ********************

import json
from delta.tables import DeltaTable
from pyspark.sql import functions as F

from fabric_lib.config import load_sources
from fabric_lib.silver import merge_condition, change_condition, dedupe_latest_sql
from fabric_lib.dq import build_checks, missing_columns

src = load_sources(p_config_root)[p_source]
bronze_tbl = f"lh_bronze.dbo.{src.bronze_table}"
silver_tbl = f"lh_silver.dbo.{src.silver_table}"

# CELL ********************

# Read only this run's bronze rows (bounded), parse API payloads if needed
df = spark.table(bronze_tbl).where(F.col("_ingest_run_id") == p_run_id)
if src.type == "rest":
    schema = spark.read.json(df.rdd.map(lambda r: r["_raw"])).schema
    df = df.select(F.from_json("_raw", schema).alias("j"), "_ingest_run_id", "_ingested_at", "_source_system").select("j.*", "_ingest_run_id", "_ingested_at", "_source_system")

# schema contract (config/silver/<dataset_id>.json: required_columns): fail fast on drift
gone = missing_columns(src.required_columns, df.columns)
if gone:
    raise ValueError(f"schema drift in {p_source}: missing {gone}")

rows_in = df.count()
df.createOrReplaceTempView("v_bronze")
latest = spark.sql(dedupe_latest_sql("v_bronze", src.business_key, src.dedupe_order_column))
latest.createOrReplaceTempView("v_latest")

# CELL ********************

# Data quality: failing rows are quarantined, the rest continue
rejected = 0
bad_keys = []
dq_rows = []
for name, sql in build_checks("v_latest", src.dq).items():
    n = spark.sql(sql).count()
    if n:
        rejected += n
        print(f"DQ FAIL {name}: {n} rows")   # counts only, never row content
        bad_keys.append(name)
        dq_rows.append((p_run_id, p_source, name, n))

clean = latest
for col in src.dq.get("not_null", []):
    clean = clean.where(F.col(col).isNotNull())
clean = clean.withColumn("_silver_updated_at", F.current_timestamp())

# CELL ********************

# Silver MERGE on business key (idempotent)
if not spark.catalog.tableExists(silver_tbl):
    clean.limit(0).write.format("delta").saveAsTable(silver_tbl)

tracked = [c for c in clean.columns if c not in src.business_key and not c.startswith("_")]
(DeltaTable.forName(spark, silver_tbl).alias("t")
    .merge(clean.alias("s"), merge_condition(src.business_key))
    .whenMatchedUpdateAll(condition=change_condition(tracked))
    .whenNotMatchedInsertAll()
    .execute())

rows_out = clean.count()

# CELL ********************

result = {"status": "succeeded", "source": p_source, "run_id": p_run_id,
          "rows_in": rows_in, "rows_out": rows_out, "rows_rejected": rejected, "dq_failed": bad_keys, "dq_rows": dq_rows}
notebookutils.notebook.exit(json.dumps(result))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
