# -*- coding: utf-8 -*-
"""The judgement tables still produce the numbers a table carries.

This is economicspace's verify.py check 6, moved with the code it checks, and
run over all eight destinations instead of whichever one was on disk.  Two
halves:

  RECOMPUTE.  Every row of every destination's table, through
    `annual_market_kg` and `in_space_utility`, against the value stored in it.
    A judgement-table edit that should have been inert is proved inert here.

  COVERAGE.  Which commodities fall through a silent default.  A name with no
    `_COMMODITY_CLASS` entry would take 15% of a destination's import budget
    (an import-time assert stops that); a name with no
    ANNUAL_WORLD_PRODUCTION_KG entry takes an UNLIMITED terrestrial market.
    `nickel-iron` is the one known, measured, deliberately unfixed instance,
    so the uncapped list is pinned: one that GROWS is the finding.
"""

import dataclasses

import pandas as pd
import pytest

import spacevalue
from spacevalue import catalog

DESTS = list(catalog.DELIVERY_DESTINATIONS)


@pytest.fixture(scope="module")
def tables(tmp_path_factory):
    out = tmp_path_factory.mktemp("tables")
    built = {}
    for d in DESTS:
        cfg = dataclasses.replace(
            catalog.CONFIG, delivery_destination=d,
            quote_snapshot="metals-2026-10-07", output_dir=str(out),
            catalog_filename=spacevalue.table_filename(d))
        built[d] = catalog.build_mineral_value_catalog(cfg)
    return built


@pytest.mark.parametrize("dest", DESTS)
def test_every_stored_value_is_what_the_tables_say(tables, dest):
    t = tables[dest]
    bad = []
    for _, r in t.iterrows():
        name = str(r["name"])
        route = str(r["value_route"]) if pd.notna(r.get("value_route")) else None
        if float(r["annual_market_kg"]) != catalog.annual_market_kg(name, dest, route):
            bad.append((name, "annual_market_kg"))
        if "in_space_utility" in t.columns and \
                float(r["in_space_utility"]) != catalog.in_space_utility(name, dest):
            bad.append((name, "in_space_utility"))
    assert not bad


def test_every_commodity_is_classified():
    names = {str(r["name"]) for r in catalog.MINERAL_REFERENCE}
    assert sorted(names - set(catalog._COMMODITY_CLASS)) == []


def test_the_uncapped_list_has_not_grown():
    """A new name here takes an unlimited terrestrial market: decide it."""
    names = {str(r["name"]) for r in catalog.MINERAL_REFERENCE}
    uncapped = sorted(n for n in names
                      if n not in catalog.ANNUAL_WORLD_PRODUCTION_KG)
    assert uncapped == UNCAPPED


@pytest.mark.parametrize("dest", DESTS)
def test_every_row_says_where_it_was_priced(tables, dest):
    assert set(tables[dest]["delivery_destination"]) == {dest}


def test_every_in_space_destination_has_a_demand_row():
    in_space = [d for d, legs in catalog._DELIVERY_LEGS.items() if legs is not None]
    assert sorted(set(in_space) - set(catalog.IN_SPACE_ANNUAL_DEMAND_KG)) == []


def test_gto_shares_geo_utility_by_reference():
    """`gto` takes geo's profile as the same object, never a copy."""
    by = catalog.IN_SPACE_UTILITY_BY_DESTINATION
    assert by["gto"] is by["geo"]


# Measured on 2026-10-26, when the package was split out.  Most are phases
# sold through their yields or as one product with another, whose ceiling is
# their product's; nickel-iron is the known, deliberately unfixed instance.
UNCAPPED = [
    "awaruite", "carbonates", "chlorapatite", "chromite", "cohenite",
    "daubreelite", "enstatite", "hibonite", "ilmenite", "kamacite", "laurite",
    "magnetite", "merrillite", "native-pgm", "nickel-iron", "niningerite",
    "oldhamite", "olivine", "orthopyroxene", "oxides", "pentlandite",
    "perovskite", "phyllosilicates", "plagioclase", "pyroxene", "pyrrhotite",
    "schreibersite", "sperrylite", "spinel", "taenite", "tetrataenite",
    "troilite",
]
