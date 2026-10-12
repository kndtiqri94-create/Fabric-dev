from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Iterator

AUDIT_COLUMNS = ("_ingest_run_id", "_ingested_at", "_source_system")


def paginate(
    fetch_page: Callable[[int], dict[str, Any]],
    records_path: str,
    max_pages: int = 10_000,
) -> Iterator[dict[str, Any]]:
    """Yield records from a page-numbered API until an empty page is returned.

    `fetch_page(n)` performs the HTTP call (retries/auth live in the caller).
    """
    for page in range(1, max_pages + 1):
        records = fetch_page(page).get(records_path, [])
        if not records:
            return
        yield from records
    raise RuntimeError(f"pagination exceeded max_pages={max_pages}")


def audit_values(run_id: str, source_system: str) -> dict[str, str]:
    return {
        "_ingest_run_id": run_id,
        "_ingested_at": datetime.now(timezone.utc).isoformat(),
        "_source_system": source_system,
    }


def delete_run_sql(table: str) -> str:
    """Makes a bronze re-run idempotent: remove rows of this run before appending."""
    return f"DELETE FROM {table} WHERE _ingest_run_id = '{{run_id}}'"
