from __future__ import annotations

from .silver import _ident


def not_null_failures_sql(view: str, column: str) -> str:
    return f"SELECT * FROM {view} WHERE {_ident(column)} IS NULL"


def duplicate_keys_sql(view: str, columns: list[str]) -> str:
    cols = ", ".join(_ident(c) for c in columns)
    return f"SELECT {cols}, COUNT(*) AS n FROM {view} GROUP BY {cols} HAVING COUNT(*) > 1"


def build_checks(view: str, dq: dict[str, list[str]]) -> dict[str, str]:
    """Return {check_name: SQL returning offending rows}. Empty result = pass."""
    checks: dict[str, str] = {}
    for col in dq.get("not_null", []):
        checks[f"not_null:{col}"] = not_null_failures_sql(view, col)
    for col in dq.get("unique", []):
        checks[f"unique:{col}"] = duplicate_keys_sql(view, [col])
    return checks


def missing_columns(expected: dict[str, str], actual: list[str]) -> list[str]:
    """Schema contract check: columns the contract requires but the data lacks."""
    have = {c.lower() for c in actual}
    return [c for c in expected if c.lower() not in have]
