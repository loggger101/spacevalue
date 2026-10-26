# -*- coding: utf-8 -*-
"""The names economicspace reads, declared here so removing one is loud.

economicspace pins a TAG of this package and installs its price releases as
its Stage 2.  Its `modules/mineral_value.py` re-exports the names below, and
the rest of that repository reads them as `master.<name>`: the destination
list feeds its command line and dashboard, its verify.py check 6 recomputes
every installed row through the judgement tables, and its worked calculation
re-derives a delivered price from the delivery names.  A name dropped between
releases is found only when somebody installs the new tag and an import fails.

A failure here does not mean the name must come back.  It means the change is
BREAKING for that consumer: a minor-version bump while this is 0.x, a line in
CHANGELOG.md, and the matching edit to economicspace's Stage 2 adapter.

The list is typed, not derived: reading it out of economicspace would need
that repository checked out, which CI does not have, and a check that skips
on every run is no check.  Refresh it by grepping economicspace's
`modules/mineral_value.py` for `spacevalue.` and `_sv.`.
"""

import spacevalue
from spacevalue import catalog

# Top-level names, each also in `__all__` so the wheel step covers them.
CONSUMER_SURFACE = (
    "__version__", "DATA_VERSION",
    "DELIVERY_DESTINATIONS", "MINERAL_REFERENCE", "ANNUAL_WORLD_PRODUCTION_KG",
    "annual_market_kg", "in_space_utility", "validate",
    "table_filename", "ASSET_MANIFEST",
)

# Private names of `spacevalue.catalog` the adapter re-exports.  A private
# name a consumer reaches is a contract all the same, and this is where it is
# written down.
CATALOG_SURFACE = (
    "_COMMODITY_CLASS", "_UNLIMITED_MARKET_KG",
    "_DELIVERY_LEGS", "_LEO_USD_PER_KG", "delivered_cost_usd_per_kg",
)

# What a published release's manifest carries that economicspace reads.
MANIFEST_KEYS = ("release_tag", "pipeline_version", "catalog_date",
                 "quote_snapshot", "destinations", "files")
FILE_KEYS = ("bytes", "sha256")


def test_every_top_level_name_still_exists():
    missing = [n for n in CONSUMER_SURFACE if not hasattr(spacevalue, n)]
    assert not missing, ("economicspace reads these and this package no longer "
                         "exports them: " + ", ".join(missing))


def test_the_top_level_contract_is_public():
    undeclared = [n for n in CONSUMER_SURFACE
                  if n not in spacevalue.__all__ and n != "__version__"]
    assert not undeclared


def test_every_catalog_name_still_exists():
    missing = [n for n in CATALOG_SURFACE if not hasattr(catalog, n)]
    assert not missing, ("economicspace reaches these and spacevalue.catalog "
                         "no longer has them: " + ", ".join(missing))


def test_a_manifest_carries_what_the_installer_reads(tmp_path):
    import json
    m = spacevalue.build_release("metals-2026-10-07", str(tmp_path))
    assert [k for k in MANIFEST_KEYS if k not in m] == []
    for entry in m["files"].values():
        assert [k for k in FILE_KEYS if k not in entry] == []
    on_disk = json.load(open(str(tmp_path / spacevalue.ASSET_MANIFEST)))
    assert on_disk == m


def test_the_table_filename_is_the_asset_name_economicspace_downloads():
    assert spacevalue.table_filename("cislunar") == "mineral_value_catalog.cislunar.csv"


def test_every_config_field_has_help():
    """economicspace's dashboard shows a field's comment block as its help.

    Its Stage 2 config is its own now, but the rule is the family's, and a
    reader of this config deserves the same.
    """
    import ast
    import inspect
    src = inspect.getsource(catalog)
    lines = src.split("\n")
    node = next(n for n in ast.walk(ast.parse(src))
                if isinstance(n, ast.ClassDef) and n.name == "MineralValueConfig")
    bare = []
    for stmt in node.body:
        if not (isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)):
            continue
        above = lines[stmt.lineno - 2].strip()
        trailing = "#" in lines[stmt.lineno - 1].split("=", 1)[-1]
        if not (above.startswith("#") or trailing):
            bare.append(stmt.target.id)
    assert not bare, "MineralValueConfig fields with no help comment: %s" % bare
