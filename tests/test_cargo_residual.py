# -*- coding: utf-8 -*-
"""A body with no named fraction is all residual, and is worth the rock floor.

AsteroidCatalog defines Unknown as the whole body being residual.  The floor
used to want some named mass first, so a blank row was worth 0 and a silicate
fraction of 1e-12 earned the whole floor.
"""

import math
import os

import pandas as pd
import pytest

from spacevalue import cargo

HERE = os.path.dirname(os.path.abspath(__file__))
FRACTIONS = ("comp_metal_fraction", "comp_silicate_fraction",
             "comp_carbon_fraction", "comp_ice_fraction")
DESTINATIONS = ("earth_surface", "cislunar")


def load(dest):
    path = os.path.join(HERE, "data", "prices-2026-10-07",
                        "mineral_value_catalog.%s.csv" % dest)
    return pd.read_csv(path, float_precision="round_trip", low_memory=False)


@pytest.fixture(params=DESTINATIONS)
def table(request):
    return load(request.param)


BLANKS = {
    "zero": dict.fromkeys(FRACTIONS, 0.0),
    "none": dict.fromkeys(FRACTIONS, None),
    "nan": dict.fromkeys(FRACTIONS, math.nan),
    "absent": {},
    "empty phases": {"comp_phases": ""},
}


def floor(table):
    return cargo._mineral_price(table, "silicates")


@pytest.mark.parametrize("name", sorted(BLANKS))
def test_a_blank_body_is_worth_the_silicate_quote(table, name):
    row = BLANKS[name]
    assert cargo.asteroid_bulk_value_usd_per_kg(row, table) == floor(table)
    assert cargo.asteroid_best_phase_usd_per_kg(row, table) == floor(table)


@pytest.mark.parametrize("name", sorted(BLANKS))
def test_a_blank_body_is_one_row_of_residual(table, name):
    assert (cargo.asteroid_phase_table(BLANKS[name], table)
            == [(cargo._RESIDUAL_PHASE, 1.0, floor(table))])


def test_the_floor_does_not_jump_at_zero(table):
    """The limit of an ever smaller silicate fraction is the blank body."""
    sliver = dict.fromkeys(FRACTIONS, 0.0)
    sliver["comp_silicate_fraction"] = 1e-12
    blank = cargo.asteroid_bulk_value_usd_per_kg(BLANKS["zero"], table)
    near = cargo.asteroid_bulk_value_usd_per_kg(sliver, table)
    assert near == pytest.approx(blank, rel=1e-9)


def test_the_residual_carries_the_silicates_ceiling(table):
    """Priced as silicates, so capped as silicates: the alias the partial case has."""
    assert cargo._PHASE_MARKET_ALIAS[cargo._RESIDUAL_PHASE] == "silicates"


def test_a_cached_blank_is_the_same_answer():
    table = load("cislunar")
    first = cargo.asteroid_bulk_value_usd_per_kg(BLANKS["zero"], table)
    assert cargo.asteroid_bulk_value_usd_per_kg(BLANKS["zero"], table) == first
    assert cargo.asteroid_phase_table(BLANKS["zero"], table) == cargo.asteroid_phase_table(
        BLANKS["zero"], table)


def test_a_negative_sum_stays_out_of_the_residual(table):
    """A malformed row is not a body with nothing named in it."""
    row = dict.fromkeys(FRACTIONS, 0.0)
    row["comp_silicate_fraction"] = -0.1
    expected = -0.1 * floor(table)
    assert cargo.asteroid_bulk_value_usd_per_kg(row, table) == pytest.approx(expected)


def test_a_named_body_is_unchanged(table):
    """No residual: the fractions already sum to 1."""
    row = dict.fromkeys(FRACTIONS, 0.0)
    row["comp_silicate_fraction"] = 1.0
    assert cargo.asteroid_bulk_value_usd_per_kg(row, table) == floor(table)
    assert [p[0] for p in cargo.asteroid_phase_table(row, table)] == ["silicates"]
