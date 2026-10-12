from __future__ import annotations

import re

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _ident(name: str) -> str:
    if not _IDENT.match(name):
        raise ValueError(f"unsafe identifier: {name!r}")
    return name


def merge_condition(keys: list[str], target: str = "t", source: str = "s") -> str:
    return " AND ".join(f"{target}.{_ident(k)} = {source}.{_ident(k)}" for k in keys)


def change_condition(columns: list[str], target: str = "t", source: str = "s") -> str:
    """Null-safe 'row changed' predicate, so unchanged rows are not rewritten."""
    return " OR ".join(
        f"NOT ({target}.{_ident(c)} <=> {source}.{_ident(c)})" for c in columns
    )


def dedupe_latest_sql(view: str, keys: list[str], order_col: str) -> str:
    """Keep the most recent record per business key (bronze may hold several versions)."""
    k = ", ".join(_ident(x) for x in keys)
    return (
        f"SELECT * EXCEPT (_rn) FROM ("
        f"SELECT *, ROW_NUMBER() OVER (PARTITION BY {k} ORDER BY {_ident(order_col)} DESC) AS _rn "
        f"FROM {view}) WHERE _rn = 1"
    )
