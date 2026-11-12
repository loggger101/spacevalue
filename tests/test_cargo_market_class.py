# -*- coding: utf-8 -*-
"""One in-space demand class is one allowance, however many commodities fill it.

`annual_market_kg` gives each commodity of a class the class's whole share of
one import budget, and the rows of a class are substitutes.  Keyed by name, each
spent a separate copy: olivine and pyroxene sold 30 t/yr into a 15 t/yr market.
"""

import os

import pandas as pd
import pytest

from spacevalue import cargo, catalog

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(HERE, "data", "prices-2026-10-07")


def load(dest):
    path = os.path.join(SEED, "mineral_value_catalog.%s.csv" % dest)
    return pd.read_csv(path, float_precision="round_trip", low_memory=False)


def terms(markets, table, sold):
    return [(kg, cargo._mineral_price(table, name),
             cargo.phase_market_kg(markets, name),
             cargo.phase_market_key(markets, name)) for name, kg in sold]


@pytest.fixture
def cislunar():
    table = load("cislunar")
    return table, cargo.market_table(table)


def test_a_class_is_one_market_at_a_destination(cislunar):
    _table, markets = cislunar
    assert (cargo.phase_market_key(markets, "olivine")
            == cargo.phase_market_key(markets, "pyroxene")
            == "in-space shielding")
    assert (cargo.phase_market_key(markets, "iron")
            == cargo.phase_market_key(markets, "titanium")
            == "in-space structural")
    assert (cargo.phase_market_key(markets, "olivine")
            != cargo.phase_market_key(markets, "iron"))


def test_the_residual_spends_the_silicates_allowance(cislunar):
    _table, markets = cislunar
    assert (cargo.phase_market_key(markets, cargo._RESIDUAL_PHASE)
            == cargo.phase_market_key(markets, "silicates"))


def test_a_row_of_a_class_carries_the_whole_class_ceiling(cislunar):
    """Which is why they must share it: nothing here splits the budget."""
    _table, markets = cislunar
    assert (cargo.phase_market_kg(markets, "olivine")
            == cargo.phase_market_kg(markets, "pyroxene") == 15_000.0)


def test_shipped_to_earth_keeps_its_own_market(cislunar):
    table, markets = cislunar
    assert cargo.phase_market_key(markets, "gold") == "gold"
    assert cargo.phase_market_key(markets, "platinum") == "platinum"
    shipped = table[table["value_route"] == "shipped to Earth"]
    assert len(shipped) > 0
    assert (shipped["market_id"] == shipped["name"]).all()


def test_earth_has_no_class_market():
    table = load("earth_surface")
    assert (table["market_id"] == table["name"]).all()


def test_two_ceilings_that_match_are_not_one_market():
    assert catalog.market_id("copper", "cislunar", "shipped to Earth") == "copper"
    assert catalog.market_id("iron", "cislunar", "shipped to Earth") == "iron"
    assert catalog.market_id("iron", "earth_surface") == "iron"


def test_a_table_with_no_market_id_keeps_a_market_per_name():
    """A published release before contract 1.19.0 reads exactly as it did."""
    table = load("cislunar").drop(columns="market_id")
    markets = cargo.market_table(table)
    assert cargo.phase_market_key(markets, "olivine") == "olivine"
    assert cargo.phase_market_key(markets, "pyroxene") == "pyroxene"
    assert cargo.phase_market_key(markets, cargo._RESIDUAL_PHASE) == "silicates"


def test_the_witness_sells_one_allowance(cislunar):
    """R330: 20 t split evenly between two rows of one 15 t market, one year."""
    table, markets = cislunar
    sale = terms(markets, table, [("olivine", 10_000.0), ("pyroxene", 10_000.0)])
    value, unsold, surplus = cargo._capped_sale_value(sale, 1.0, 0.5)
    assert value == pytest.approx(28_054_272, abs=1)
    assert (unsold, surplus) == (0.0, 5_000.0)
    # The same sale with a market per name: the whole load at full price.
    old = [(kg, price, cap, name) for (kg, price, cap, _key), name
           in zip(sale, ("olivine", "pyroxene"))]
    assert cargo._capped_sale_value(old, 1.0, 0.5)[0] == pytest.approx(32_062_025, abs=1)


@pytest.mark.parametrize("first", [0, 1])
def test_a_pooled_allowance_goes_to_the_dearer_phase(first):
    """Whichever order the sale arrives in."""
    sale = [(10.0, 100.0, 12.0, "m"), (10.0, 50.0, 12.0, "m")]
    if first:
        sale.reverse()
    value, unsold, surplus = cargo._capped_sale_value(sale, 1.0, 0.0)
    assert value == 10.0 * 100.0 + 2.0 * 50.0
    assert (unsold, surplus) == (8.0, 0.0)


def test_a_discount_sells_what_the_allowance_left():
    sale = [(10.0, 50.0, 12.0, "m"), (10.0, 100.0, 12.0, "m")]
    value, unsold, surplus = cargo._capped_sale_value(sale, 1.0, 0.5)
    assert value == 10.0 * 100.0 + 2.0 * 50.0 + 8.0 * 50.0 * 0.5
    assert (unsold, surplus) == (0.0, 8.0)


def test_a_sale_nothing_pools_sums_in_its_own_order():
    """Order is load-bearing on the last bit; see `optimal_payload_mix`."""
    sale = [(0.1, 3.3, float("inf"), "a"), (0.2, 7.7, float("inf"), "b"),
            (0.3, 1.1, float("inf"), "c")]
    assert cargo._capped_sale_value(sale, 1.0, 0.5)[0] == 0.1 * 3.3 + 0.2 * 7.7 + 0.3 * 1.1


def test_the_knapsack_spends_one_allowance_too(cislunar):
    table, markets = cislunar
    phases = [("olivine", 0.5, cargo._mineral_price(table, "olivine")),
              ("pyroxene", 0.5, cargo._mineral_price(table, "pyroxene"))]
    keys = {n: cargo.phase_market_key(markets, n) for n, _f, _p in phases}
    caps = {"in-space shielding": 15_000.0}
    mix = cargo.optimal_payload_mix(20_000.0, 100_000.0, phases, 1.0,
                                    caps=caps, cap_keys=keys, surplus_price_frac=0.5)
    assert mix["surplus_kg"] == pytest.approx(5_000.0)
    assert sum(mix["mix_kg"].values()) == pytest.approx(20_000.0)
    assert caps["in-space shielding"] == 0.0
