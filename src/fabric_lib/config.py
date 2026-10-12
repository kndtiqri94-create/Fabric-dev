"""Reads the layered metadata under config/.

    framework_config.json  global settings only
    connections/<name>.json  how to reach a system (references to Key Vault secret names, never values)
    sources/<dataset_id>.json  what to extract (sql{} or rest{})
    bronze/<dataset_id>.json   how raw data lands
    silver/<dataset_id>.json   keys, dedupe, DQ rules, schema contract
    gold/<target>.json         warehouse table, load procedure, dependencies
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from graphlib import TopologicalSorter
from pathlib import Path
from typing import Any

AUTH_MODES = ("none", "bearer", "api_key")


def _read(root: str, *parts: str) -> dict[str, Any]:
    return json.loads(Path(root, *parts).read_text(encoding="utf-8"))


def _read_dir(root: str, folder: str) -> dict[str, dict[str, Any]]:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(root, folder).glob("*.json"))}


@dataclass(frozen=True)
class Source:
    """One dataset, merged from its connection + source + bronze + silver files."""
    name: str                       # dataset_id
    type: str                       # sql | rest
    connection: str
    load_mode: str
    business_key: list[str]
    bronze_table: str
    silver_table: str
    watermark_column: str | None = None
    # sql
    sql_table: str | None = None
    sql_query: str | None = None
    # rest (endpoint from source; base_url/auth/secret from the connection)
    base_url: str | None = None
    source_object: str | None = None
    auth: str = "none"
    auth_header: str = "X-API-Key"
    secret_name: str | None = None
    watermark_param: str | None = None
    pagination: dict[str, Any] = field(default_factory=dict)
    records_path: str | None = None
    # bronze / silver
    bronze_write_mode: str = "append"
    partition_by: list[str] = field(default_factory=list)
    dedupe_order_column: str = "_ingested_at"
    required_columns: dict[str, str] = field(default_factory=dict)
    dq: dict[str, list[str]] = field(default_factory=dict)
    enabled: bool = True
    additional_config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.type not in ("sql", "rest"):
            raise ValueError(f"{self.name}: unsupported source_type {self.type!r}")
        if self.load_mode not in ("full", "incremental"):
            raise ValueError(f"{self.name}: unsupported load_mode {self.load_mode!r}")
        if self.load_mode == "incremental" and not self.watermark_column:
            raise ValueError(f"{self.name}: incremental load needs watermark_column")
        if not self.business_key:
            raise ValueError(f"{self.name}: silver.business_key is required")
        if not self.bronze_table or not self.silver_table:
            raise ValueError(f"{self.name}: bronze.table and silver.table are required")
        if self.type == "sql" and not (self.sql_table or self.sql_query):
            raise ValueError(f"{self.name}: sql needs table or query")
        if self.type == "rest":
            if self.auth not in AUTH_MODES:
                raise ValueError(f"{self.name}: unsupported auth {self.auth!r}")
            if self.auth != "none" and not self.secret_name:
                raise ValueError(f"{self.name}: auth={self.auth} needs secret_name on the connection")
            if self.pagination.get("style") not in ("page", "offset"):
                raise ValueError(f"{self.name}: rest needs pagination.style page|offset")
            if not (self.base_url and self.source_object):
                raise ValueError(f"{self.name}: rest needs connection base_url and source endpoint")
            if self.load_mode == "incremental" and not self.watermark_param:
                raise ValueError(f"{self.name}: incremental rest needs watermark_param")


@dataclass(frozen=True)
class Gold:
    target: str                     # e.g. gold.fact_orders
    procedure: str
    load_type: str                  # upsert | full_refresh
    depends_on_silver: list[str] = field(default_factory=list)
    depends_on_gold: list[str] = field(default_factory=list)
    enabled: bool = True

    @property
    def name(self) -> str:
        return self.target.split(".")[-1]

    def __post_init__(self) -> None:
        if self.load_type not in ("upsert", "full_refresh"):
            raise ValueError(f"{self.target}: unsupported load_type {self.load_type!r}")
        if not self.procedure:
            raise ValueError(f"{self.target}: procedure is required")


def load_framework(config_root: str) -> dict[str, Any]:
    return _read(config_root, "framework_config.json")


def load_connection(config_root: str, name: str) -> dict[str, Any]:
    return _read(config_root, "connections", f"{name}.json")


def load_sources(config_root: str, include_disabled: bool = False) -> dict[str, Source]:
    sources_meta = _read_dir(config_root, "sources")
    bronze, silver = _read_dir(config_root, "bronze"), _read_dir(config_root, "silver")
    out: dict[str, Source] = {}
    for key, src in sources_meta.items():
        did = src["dataset_id"]
        if did != key:
            raise ValueError(f"sources/{key}.json: dataset_id {did!r} must match the file name")
        if did not in bronze or did not in silver:
            raise ValueError(f"{did}: needs bronze/{did}.json and silver/{did}.json")
        t = src["source_type"]
        ext, conn = src[t], load_connection(config_root, src["connection"])
        b, s = bronze[did], silver[did]
        common = dict(
            name=did, type=t, connection=src["connection"],
            load_mode=ext.get("load_mode", "full"), watermark_column=ext.get("watermark_column"),
            business_key=s.get("business_key", []),
            bronze_table=b.get("table", ""), silver_table=s.get("table", ""),
            bronze_write_mode=b.get("write_mode", "append"), partition_by=b.get("partition_by", []),
            dedupe_order_column=s.get("dedupe_order_column", "_ingested_at"),
            required_columns=s.get("required_columns", {}), dq=s.get("dq", {}),
            enabled=src.get("enabled", True), additional_config=src.get("additional_config", {}),
        )
        if t == "sql":
            out[did] = Source(**common, sql_table=ext.get("table"), sql_query=ext.get("query"))
        else:
            out[did] = Source(
                **common, base_url=conn.get("base_url"), source_object=ext.get("endpoint"),
                auth=conn.get("auth", "none"), auth_header=conn.get("auth_header", "X-API-Key"),
                secret_name=conn.get("secret_name"), watermark_param=ext.get("watermark_param"),
                pagination=ext.get("pagination", {}), records_path=ext.get("records_path"),
            )
    return {k: v for k, v in out.items() if include_disabled or v.enabled}


def load_gold(config_root: str, include_disabled: bool = False) -> dict[str, Gold]:
    out = {name: Gold(**g) for name, g in _read_dir(config_root, "gold").items()}
    return {k: v for k, v in out.items() if include_disabled or v.enabled}


def gold_load_order(gold: dict[str, Gold]) -> list[str]:
    """Targets in dependency order (dimensions before facts). Raises on cycles / unknown deps."""
    graph = {}
    for name, g in gold.items():
        unknown = [d for d in g.depends_on_gold if d not in gold]
        if unknown:
            raise ValueError(f"{name}: depends_on_gold references unknown {unknown}")
        graph[name] = set(g.depends_on_gold)
    return list(TopologicalSorter(graph).static_order())
