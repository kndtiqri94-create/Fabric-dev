"""Control metadata stored in the dedicated lh_metadata lakehouse (schema `meta`).

Tables: watermark, run_log, dq_result (Delta). Keeps pure helpers here so they are unit-testable;
the Spark I/O lives in notebooks/nb_metadata_ops.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# Column order = table schema. Types are Spark SQL.
SCHEMAS: dict[str, dict[str, str]] = {
    "watermark": {"source_name": "STRING", "watermark_value": "STRING", "updated_at": "TIMESTAMP"},
    "run_log": {
        "run_id": "STRING", "source_name": "STRING", "layer": "STRING", "status": "STRING",
        "rows_in": "BIGINT", "rows_out": "BIGINT", "rows_rejected": "BIGINT", "logged_at": "TIMESTAMP",
    },
    "dq_result": {
        "run_id": "STRING", "source_name": "STRING", "check_name": "STRING",
        "failed_rows": "BIGINT", "logged_at": "TIMESTAMP",
    },
}


def create_table_sql(full_name: str, table: str) -> str:
    cols = ", ".join(f"{c} {t}" for c, t in SCHEMAS[table].items())
    return f"CREATE TABLE IF NOT EXISTS {full_name} ({cols}) USING DELTA"


def _parse(v: str) -> float | datetime:
    try:
        return float(v)
    except ValueError:
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def advance_watermark(current: str | None, new: str | None) -> str | None:
    """Watermarks only move forward: a re-run with older data must never rewind the bookmark."""
    if not new:
        return current
    if not current:
        return new
    return new if _parse(new) > _parse(current) else current


def run_log_row(run_id: str, source: str, layer: str, result: dict[str, Any]) -> dict[str, Any]:
    """Build a run_log row from a notebook/pipeline exit value. Counts and ids only, never data."""
    return {
        "run_id": run_id, "source_name": source, "layer": layer,
        "status": result.get("status", "failed"),
        "rows_in": int(result.get("rows_in") or 0), "rows_out": int(result.get("rows_out") or 0),
        "rows_rejected": int(result.get("rows_rejected") or 0),
        "logged_at": datetime.now(timezone.utc),
    }


def dq_rows(run_id: str, source: str, failures: list[tuple[str, int]]) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    return [{"run_id": run_id, "source_name": source, "check_name": n, "failed_rows": int(c), "logged_at": now}
            for n, c in failures]
