# -*- coding: utf-8 -*-
"""`asteroid_refinery` remembers a composition, and only ever saves it time.

The phase loop used to overwrite the composition key with a phase name, so the
memo was never filled and a composition `_composition_key` declines reached the
write with nothing bound.  `tests/test_cargo_golden.py` holds the numbers.
"""

from decimal import Decimal
import os

import pandas as pd
import pytest

from spacevalue import cargo

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(HERE, "data", "prices-2026-10-07",
                     "mineral_value_catalog.cislunar.csv")
ROW = {"comp_metal_fraction": 0.01, "comp_silicate_fraction": 0.6,
       "comp_carbon_fraction": 0.03, "comp_ice_fraction": 0.1}


@pytest.fixture
def table():
    return pd.read_csv(TABLE, float_precision="round_trip", low_memory=False)


@pytest.fixture
def flown(table):
    """The table as Stage 4 holds it when the refinery flies."""
    table[cargo._NET_PRICE_COL] = table["price_usd_per_kg"]
    return table


@pytest.fixture
def walks(monkeypatch):
    """How many times the phase walk ran."""
    calls = []
    real = cargo._phase_terms

    def counted(*args):
        calls.append(args[1])
        return real(*args)

    monkeypatch.setattr(cargo, "_phase_terms", counted)
    return calls


def test_a_repeated_composition_is_walked_once(flown, walks):
    first = cargo.asteroid_refinery(dict(ROW), flown)
    assert walks, "the walk ran"
    n = len(walks)
    again = cargo.asteroid_refinery(dict(ROW), flown)
    assert len(walks) == n, "the second call was answered by the memo"
    assert again == first


def test_two_spellings_of_a_gap_share_an_answer(flown, walks):
    first = cargo.asteroid_refinery({**ROW, "comp_ice_fraction": None}, flown)
    n = len(walks)
    assert cargo.asteroid_refinery({**ROW, "comp_ice_fraction": float("nan")},
                                   flown) == first
    assert len(walks) == n


def test_compositions_do_not_share_an_answer(flown):
    a = cargo.asteroid_refinery(dict(ROW), flown)
    b = cargo.asteroid_refinery({**ROW, "comp_metal_fraction": 0.3}, flown)
    assert a != b


def test_an_empty_composition_is_remembered_too(flown):
    first = cargo.asteroid_refinery({}, flown)
    assert cargo.asteroid_refinery({}, flown) == first


def test_a_composition_the_memo_declines_gets_the_same_answer(flown):
    """Decimal is finite and not a float: uncached, not an error."""
    held = cargo.asteroid_refinery(dict(ROW), flown)
    row = {**ROW, "comp_metal_fraction": Decimal("0.01")}
    assert cargo._composition_key(row) is None
    assert cargo.asteroid_refinery(row, flown) == held


def test_no_refinery_no_answer(table):
    assert cargo.asteroid_refinery(dict(ROW), table) is None
