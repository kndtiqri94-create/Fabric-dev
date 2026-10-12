import glob
import re

from fabric_lib.config import load_framework
from fabric_lib.meta import SCHEMAS, advance_watermark, create_table_sql, dq_rows, run_log_row


def test_watermark_never_moves_backwards():
    assert advance_watermark(None, "2026-09-04T10:00:00") == "2026-09-04T10:00:00"
    assert advance_watermark("2026-09-05T08:30:00", "2026-09-04T10:00:00") == "2026-09-05T08:30:00"
    assert advance_watermark("2026-09-04T10:00:00", "2026-09-05T08:30:00") == "2026-09-05T08:30:00"
    assert advance_watermark("2026-09-04T10:00:00", "") == "2026-09-04T10:00:00"


def test_watermark_numeric_and_timezones():
    assert advance_watermark("9", "10") == "10"                     # numeric, not string compare
    assert advance_watermark("2026-09-04T10:00:00Z", "2026-09-04T09:00:00+00:00") == "2026-09-04T10:00:00Z"


def test_run_log_row_counts_only():
    row = run_log_row("r1", "orders_sql", "silver", {"status": "succeeded", "rows_in": 4, "rows_out": 4, "secret": "x"})
    assert set(row) == set(SCHEMAS["run_log"])
    assert row["rows_in"] == 4 and row["rows_rejected"] == 0
    assert run_log_row("r", "s", "bronze", {})["status"] == "failed"    # missing status = failure


def test_dq_rows_shape():
    rows = dq_rows("r1", "orders_sql", [("not_null:OrderID", 2)])
    assert set(rows[0]) == set(SCHEMAS["dq_result"]) and rows[0]["failed_rows"] == 2


def test_create_table_sql():
    assert "CREATE TABLE IF NOT EXISTS lh_metadata.meta.watermark (source_name STRING" in create_table_sql("lh_metadata.meta.watermark", "watermark")


def test_control_tables_live_in_metadata_lakehouse():
    c = load_framework("config")
    lh = c["layers"]["metadata"]["lakehouse"]
    assert lh == "lh_metadata"
    assert all(t.startswith(f"{lh}.meta.") for t in c["control"].values())
    assert set(c["control"].values()) == {f"lh_metadata.meta.{t}" for t in SCHEMAS}


def test_warehouse_sql_reads_metadata_lakehouse_not_local_etl():
    sql = "".join(open(f, encoding="utf-8").read() for f in glob.glob("warehouse/**/*.sql", recursive=True))
    assert not re.search(r"\betl\.", sql)
    assert "lh_metadata.meta.run_log" in sql
