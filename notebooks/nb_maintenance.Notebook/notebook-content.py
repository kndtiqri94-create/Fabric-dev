# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": { "name": "synapse_pyspark" }
# META }

# PARAMETERS CELL ********************

p_lakehouses = ["lh_bronze", "lh_silver", "lh_metadata"]
p_retain_hours = 168      # >=168h unless an exception is recorded

# CELL ********************

assert p_retain_hours >= 168, "VACUUM retention below 7 days requires a recorded exception"
for lh in p_lakehouses:
    schema = "meta" if lh == "lh_metadata" else "dbo"
    for t in spark.sql(f"SHOW TABLES IN {lh}.{schema}").collect():
        full = f"{lh}.{schema}.{t.tableName}"
        spark.sql(f"OPTIMIZE {full}")
        spark.sql(f"VACUUM {full} RETAIN {p_retain_hours} HOURS")
        print(f"maintained {full}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
