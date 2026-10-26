# -*- coding: utf-8 -*-
"""A table built from the seed snapshot is the table economicspace measured on.

`tests/data/prices-2026-10-07/` holds the eight tables built from
`metals-2026-10-07`.  When this package was split out, those eight were shown
equal to economicspace's mineral_value 1.16.0 fed the same five closes, and
seven of them (gto is newer) equal, byte for byte once the stamp is swapped,
to the tables economicspace froze at 1.15.0 and ran its cells against.  So
these fixtures are that history, and a byte moving here is a number moving
there.

THE PROMISE IS PER PLATFORM.  The in-space prices go through the rocket
equation in spacecost, which calls `math.exp`, and a C library's `exp` may
round the last bit differently from another's.  The fixtures were written on
Windows; a mismatch elsewhere fails with the columns that moved, so a reader
can tell a last-bit difference from a real one.
"""

import dataclasses
import os

import pandas as pd
import pytest

import spacevalue
from spacevalue import catalog

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "data", "prices-2026-10-07")
DESTS = list(catalog.DELIVERY_DESTINATIONS)


def _build(dest, out, **extra):
    cfg = dataclasses.replace(
        catalog.CONFIG, delivery_destination=dest,
        quote_snapshot="metals-2026-10-07", output_dir=str(out),
        catalog_filename=spacevalue.table_filename(dest), **extra)
    catalog.build_mineral_value_catalog(cfg)
    return os.path.join(str(out), cfg.catalog_filename)


def test_there_is_a_fixture_for_every_destination():
    have = sorted(f for f in os.listdir(FIXTURES) if f.endswith(".csv"))
    assert have == sorted(spacevalue.table_filename(d) for d in DESTS)


@pytest.mark.parametrize("dest", DESTS)
def test_the_seed_rebuilds_its_table_byte_for_byte(dest, tmp_path):
    built = _build(dest, tmp_path)
    want = os.path.join(FIXTURES, spacevalue.table_filename(dest))
    a, b = open(built, "rb").read(), open(want, "rb").read()
    if a != b:
        x = pd.read_csv(built, float_precision="round_trip")
        y = pd.read_csv(want, float_precision="round_trip")
        moved = [c for c in y.columns if c in x.columns and not x[c].equals(y[c])]
        pytest.fail("%s moved; columns that differ: %s" % (dest, moved))


def test_a_planted_utility_change_is_caught(tmp_path, monkeypatch):
    """The comparison above can fail: nudge one judgement and it does."""
    monkeypatch.setitem(catalog.IN_SPACE_UTILITY, "water", 0.99)
    built = _build("cislunar", tmp_path)
    want = os.path.join(FIXTURES, spacevalue.table_filename("cislunar"))
    assert open(built, "rb").read() != open(want, "rb").read()


def test_the_table_is_dated_by_its_quotes_not_by_the_run(tmp_path):
    t = pd.read_csv(_build("leo", tmp_path))
    assert set(t["catalog_date"]) == {"2026-10-07"}
    assert set(t["pipeline_version"]) == {spacevalue.DATA_VERSION}


def test_the_five_quoted_rows_carry_their_closes(tmp_path):
    t = pd.read_csv(_build("earth_surface", tmp_path), float_precision="round_trip")
    quoted = t.dropna(subset=["live_price_source"]).set_index("name")
    assert quoted["live_price_usd_per_kg"].to_dict() == {
        "gold":      4175.2998046875 * catalog.TROY_OZ_PER_KG,
        "platinum":  1713.4000244140625 * catalog.TROY_OZ_PER_KG,
        "palladium": 1212.5 * catalog.TROY_OZ_PER_KG,
        "silver":    61.2599983215332 * catalog.TROY_OZ_PER_KG,
        "copper":    6.6479997634887695 * catalog.LB_PER_KG,
    }
    assert set(quoted["live_price_date"]) == {"2026-09-29"}
