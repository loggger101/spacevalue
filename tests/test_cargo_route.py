# -*- coding: utf-8 -*-
"""`sold_as_is` offers the as-is route; the net-price route stays the default.

rc-279: at LEO, magnetite refines on net prices while its gross price and its
energy are both lower as it is.  `tests/test_cargo_golden.py` holds every float
of the default.
"""

import json
import os

import pandas as pd
import pytest

from spacevalue import cargo

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(HERE, "data", "prices-2026-10-07",
                     "mineral_value_catalog.leo.csv")
MAGNETITE = {"comp_phases": json.dumps({"magnetite": 1.0}),
             "comp_pgm_enrichment": 1.0}


@pytest.fixture
def table():
    return pd.read_csv(TABLE, float_precision="round_trip", low_memory=False)


@pytest.fixture
def flown(table):
    """The table as Stage 4 holds it when the refinery flies."""
    table[cargo._NET_PRICE_COL] = table["price_usd_per_kg"]
    table["price_usd_per_kg"] = table["price_before_processing_usd_per_kg"]
    return table


def test_magnetite_changes_route(flown):
    gross, wh = cargo._phase_terms(flown, "magnetite", 1.0, True)
    sold_gross, sold_wh = cargo._phase_terms(
        cargo.sold_as_is(flown), "magnetite", 1.0, True)
    assert sold_gross < gross
    assert sold_wh < wh
    assert sold_gross == flown.set_index("name").loc["magnetite",
                                                     "price_usd_per_kg"]


def test_price_and_energy_follow_one_route_through_a_body(flown):
    as_is = cargo.sold_as_is(flown)
    row = dict(MAGNETITE)
    price = cargo.asteroid_phase_table(row, as_is)[0][2]
    wh = cargo.asteroid_refinery(row, as_is)[0]["magnetite"]
    assert (price, wh) == cargo._phase_terms(as_is, "magnetite", 1.0, True)
    assert price < cargo.asteroid_phase_table(row, flown)[0][2]


def test_the_original_table_keeps_its_route(flown):
    before = cargo._phase_terms(flown, "magnetite", 1.0, True)
    cargo.sold_as_is(flown)
    assert cargo._phase_terms(flown, "magnetite", 1.0, True) == before
    assert cargo._SOLD_AS_IS_COL not in flown.columns


def test_phases_limits_it_to_the_names_given(flown):
    other = cargo.sold_as_is(flown, phases=["olivine"])
    assert (cargo._phase_terms(other, "magnetite", 1.0, True)
            == cargo._phase_terms(flown, "magnetite", 1.0, True))


def test_a_phase_with_no_as_is_price_keeps_its_one_route(flown):
    flown.loc[flown["name"] == "magnetite", "price_usd_per_kg"] = float("nan")
    expected = cargo._phase_terms(flown, "magnetite", 1.0, True)
    assert (cargo._phase_terms(cargo.sold_as_is(flown), "magnetite", 1.0, True)
            == expected)


def test_a_table_with_no_refinery_is_refused(table):
    with pytest.raises(ValueError, match="refinery"):
        cargo.sold_as_is(table)
