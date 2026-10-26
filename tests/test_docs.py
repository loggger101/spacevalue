# -*- coding: utf-8 -*-
"""The README's numbers are the code's numbers.

A figure typed in prose rots the moment the code under it moves, and nobody
rereads prose to find out.  So the one table of numbers the README carries is
held to `DELIVERY_DESTINATIONS` here, row by row, both ways.
"""

import os
import re

import spacevalue

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _readme_destinations():
    text = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    rows = re.findall(r"^\| `([a-z_]+)` \| ([\d,]+) \|", text, re.M)
    return {name: int(value.replace(",", "")) for name, value in rows}


def test_every_destination_is_in_the_readme_table_and_nothing_else():
    assert sorted(_readme_destinations()) == sorted(spacevalue.DELIVERY_DESTINATIONS)


def test_each_readme_price_is_the_derived_price():
    for name, typed in _readme_destinations().items():
        derived = spacevalue.DELIVERY_DESTINATIONS[name]["usd_per_kg"]
        assert typed == round(derived), (name, typed, derived)


def test_each_readme_delta_v_is_the_chain_total():
    text = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    for name, entry in spacevalue.DELIVERY_DESTINATIONS.items():
        dv = entry["dv_above_leo_m_s"]
        if not dv:
            continue
        row = re.search(r"^\| `%s` \|[^\n]*" % name, text, re.M).group(0)
        assert "{:,.0f} m/s".format(dv) in row, (name, row)
