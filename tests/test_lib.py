import pytest

from fabric_lib.bronze import paginate
from fabric_lib.config import Source
from fabric_lib.dq import build_checks, missing_columns
from fabric_lib.silver import change_condition, merge_condition


def test_paginate_stops_on_empty_page():
    pages = {1: {"data": [{"id": 1}, {"id": 2}]}, 2: {"data": [{"id": 3}]}, 3: {"data": []}}
    assert [r["id"] for r in paginate(lambda n: pages[n], "data")] == [1, 2, 3]


def test_paginate_guards_runaway():
    with pytest.raises(RuntimeError):
        list(paginate(lambda n: {"data": [{"id": n}]}, "data", max_pages=3))


def test_merge_condition_composite_key():
    assert merge_condition(["a", "b"]) == "t.a = s.a AND t.b = s.b"


def test_unsafe_identifier_rejected():
    with pytest.raises(ValueError):
        merge_condition(["a; DROP TABLE x"])


def test_change_condition_is_null_safe():
    assert change_condition(["x"]) == "NOT (t.x <=> s.x)"


def test_build_checks():
    checks = build_checks("v", {"not_null": ["id"], "unique": ["id"]})
    assert set(checks) == {"not_null:id", "unique:id"}


def _sql(**kw):
    base = dict(name="s", type="sql", connection="c", load_mode="full", business_key=["id"],
                bronze_table="b", silver_table="s", sql_table="dbo.T")
    base.update(kw)
    return Source(**base)


def _rest(**kw):
    base = dict(name="a", type="rest", connection="c", load_mode="full", business_key=["id"],
                bronze_table="b", silver_table="s", base_url="https://x", source_object="/x",
                pagination={"style": "page"})
    base.update(kw)
    return Source(**base)


def test_incremental_requires_watermark():
    with pytest.raises(ValueError):
        _sql(load_mode="incremental")


def test_sql_needs_table_or_query():
    with pytest.raises(ValueError):
        _sql(sql_table=None)


def test_rest_auth_validation():
    assert _rest().auth == "none"
    assert _rest(auth="bearer", secret_name="kv-name").auth == "bearer"
    with pytest.raises(ValueError):
        _rest(auth="basic")
    with pytest.raises(ValueError):
        _rest(auth="bearer")            # needs secret_name


def test_rest_needs_pagination_and_watermark_param():
    with pytest.raises(ValueError):
        _rest(pagination={})
    with pytest.raises(ValueError):
        _rest(load_mode="incremental", watermark_column="u")


def test_catalogue_loads_enabled_only():
    from fabric_lib.config import load_sources
    assert set(load_sources("config")) == {"orders_sql", "customers_sql", "products_api"}
    assert "crm_contacts_api" in load_sources("config", include_disabled=True)


def test_rest_source_inherits_connection_settings():
    from fabric_lib.config import load_sources
    crm = load_sources("config", include_disabled=True)["crm_contacts_api"]
    assert crm.auth == "bearer" and crm.secret_name and crm.base_url.startswith("https://")


def test_layer_files_are_consistent():
    """Every source has bronze+silver, no orphan layer files, connections exist."""
    import glob, os
    stems = lambda d: {os.path.basename(f)[:-5] for f in glob.glob(f"config/{d}/*.json")}
    assert stems("sources") == stems("bronze") == stems("silver")
    from fabric_lib.config import load_sources
    for s in load_sources("config", include_disabled=True).values():
        assert os.path.exists(f"config/connections/{s.connection}.json"), s.name


def test_gold_dependencies_and_procedures():
    import glob
    from fabric_lib.config import gold_load_order, load_gold, load_sources
    gold = load_gold("config")
    silver = set(load_sources("config"))
    sql = "".join(open(f, encoding="utf-8").read() for f in glob.glob("warehouse/**/*.sql", recursive=True))
    for g in gold.values():
        assert g.procedure in sql, g.target
        assert set(g.depends_on_silver) <= silver, g.target
    order = gold_load_order(gold)
    assert order.index("dim_customer") < order.index("fact_orders")


def test_gold_cycle_detected():
    from fabric_lib.config import Gold, gold_load_order
    import graphlib
    a = Gold(target="gold.a", procedure="p", load_type="upsert", depends_on_gold=["b"])
    b = Gold(target="gold.b", procedure="p", load_type="upsert", depends_on_gold=["a"])
    with pytest.raises(graphlib.CycleError):
        gold_load_order({"a": a, "b": b})


def test_no_secrets_in_any_config_file():
    import glob, json, re
    bad = {"password", "pwd", "token", "client_secret", "api_key"}
    def keys(o):
        if isinstance(o, dict):
            for k, v in o.items():
                yield k.lower(); yield from keys(v)
        elif isinstance(o, list):
            for v in o: yield from keys(v)
    for f in glob.glob("config/**/*.json", recursive=True):
        text = open(f, encoding="utf-8").read()
        assert not re.search(r"://[^/\s:@]+:[^/\s@]+@", text), f   # user:pass@host
        assert not (bad & set(keys(json.loads(text)))), f


def test_missing_columns_case_insensitive():
    assert missing_columns({"ID": "int", "Email": "string"}, ["id"]) == ["Email"]
