# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": { "name": "synapse_pyspark" }
# META }

# PARAMETERS CELL ********************

p_action = "init"          # init | get_watermark | commit_watermark | log_run | log_dq
p_source = ""
p_layer = ""               # bronze | silver | gold (log_run)
p_run_id = ""
p_value = ""               # commit_watermark: new watermark
p_payload = "{}"           # log_run: notebook exit JSON; log_dq: {"dq_rows": [[run_id, source, check, n], ...]}
p_config_root = "/lakehouse/default/Files/config"   # lh_metadata attached as default lakehouse

# CELL ********************

import json
from datetime import datetime, timezone
from delta.tables import DeltaTable

from fabric_lib.config import load_framework
from fabric_lib.meta import SCHEMAS, create_table_sql, advance_watermark, run_log_row, dq_rows

ctl = load_framework(p_config_root)["control"]
T = {"watermark": ctl["watermark_table"], "run_log": ctl["run_log_table"], "dq_result": ctl["dq_table"]}

def table_df(name, rows):
    cols = ", ".join(f"{c} {t}" for c, t in SCHEMAS[name].items())
    return spark.createDataFrame([tuple(r[c] for c in SCHEMAS[name]) for r in rows], cols)

# CELL ********************

out = {"status": "succeeded", "action": p_action}

if p_action == "init":
    for name, full in T.items():
        spark.sql(create_table_sql(full, name))

elif p_action == "get_watermark":
    rows = spark.table(T["watermark"]).where(f"source_name = '{p_source}'").collect()
    out["watermark"] = rows[0]["watermark_value"] if rows else ""

elif p_action == "commit_watermark":
    # only after gold succeeded; never moves backwards
    rows = spark.table(T["watermark"]).where(f"source_name = '{p_source}'").collect()
    current = rows[0]["watermark_value"] if rows else None
    final = advance_watermark(current, p_value)
    new = table_df("watermark", [{"source_name": p_source, "watermark_value": final,
                                  "updated_at": datetime.now(timezone.utc)}])
    (DeltaTable.forName(spark, T["watermark"]).alias("t")
        .merge(new.alias("s"), "t.source_name = s.source_name")
        .whenMatchedUpdateAll().whenNotMatchedInsertAll().execute())
    out["watermark"] = final

elif p_action == "log_run":
    row = run_log_row(p_run_id, p_source, p_layer, json.loads(p_payload))
    table_df("run_log", [row]).write.format("delta").mode("append").saveAsTable(T["run_log"])

elif p_action == "log_dq":
    failures = [(r[2], r[3]) for r in json.loads(p_payload).get("dq_rows", [])]
    rows = dq_rows(p_run_id, p_source, failures)
    if rows:
        table_df("dq_result", rows).write.format("delta").mode("append").saveAsTable(T["dq_result"])
else:
    raise ValueError(f"unknown action {p_action!r}")

notebookutils.notebook.exit(json.dumps(out))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
