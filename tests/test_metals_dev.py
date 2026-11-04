# -*- coding: utf-8 -*-
"""A metals.dev quote is dated by metals.dev, never by the clock it was read on.

The payloads below are the shape of the provider's documented latest response,
with its example values; no key is used and no request leaves this machine.
"""

import dataclasses
import types

import pandas as pd
import pytest

from spacevalue import catalog

PRICES = {"gold": 1923.86, "silver": 22.905, "platinum": 916.569, "palladium": 1229.684}
METAL_STAMP = "2023-07-05T06:16:02.829Z"
CURRENCY_STAMP = "2023-07-05T06:14:08.729Z"


def _latest(**stamps):
    return {"status": "success", "currency": "USD", "unit": "toz",
            "metals": dict(PRICES), **stamps}


def _fetch(monkeypatch, payload):
    """`fetch_metals_dev` against `payload`, and what it said while reading it."""
    said = []
    monkeypatch.setattr(catalog, "say", said.append)
    response = types.SimpleNamespace(raise_for_status=lambda: None, json=lambda: payload)
    fake = types.SimpleNamespace(get=lambda url, params, timeout: response)
    monkeypatch.setitem(__import__("sys").modules, "requests", fake)
    cfg = dataclasses.replace(catalog.CONFIG, metals_api_key="OFFLINE")
    return catalog.fetch_metals_dev(cfg), said


@pytest.mark.parametrize("stamps, day", [
    ({"timestamps": {"metal": METAL_STAMP, "currency": CURRENCY_STAMP}}, "2023-07-05"),
    ({"timestamp": METAL_STAMP}, "2023-07-05"),
    ({"date": "2023-07-04"}, "2023-07-04"),
    ({"timestamp_iso": "2023-07-03T22:00:00Z"}, "2023-07-03"),
    ({"timestamps": {"metal": "not a time"}, "date": "2023-07-04"}, "2023-07-04"),
    # The day is UTC's, on either side of midnight.
    ({"timestamps": {"metal": "2023-07-05T23:59:59.999Z"}}, "2023-07-05"),
    ({"timestamps": {"metal": "2023-07-06T00:00:00.000Z"}}, "2023-07-06"),
    ({"timestamps": {"metal": "2023-07-05T23:30:00-05:00"}}, "2023-07-06"),
    ({"timestamps": {"metal": "2023-07-06T01:30:00+05:00"}}, "2023-07-05"),
])
def test_the_quote_date_is_the_providers(monkeypatch, stamps, day):
    frame, said = _fetch(monkeypatch, _latest(**stamps))
    assert set(frame["live_price_date"]) == {day}
    assert not any("WARN" in line for line in said)


@pytest.mark.parametrize("stamps", [
    {},
    {"timestamps": {"currency": CURRENCY_STAMP}},
    {"timestamps": {"metal": "not a time"}},
    {"timestamp": 1688537762},
])
def test_no_metal_timestamp_leaves_the_date_blank_and_says_so(monkeypatch, stamps):
    frame, said = _fetch(monkeypatch, _latest(**stamps))
    assert len(frame) == len(PRICES), "the prices are still good"
    assert frame["live_price_date"].isna().all()
    assert sum("no metal timestamp" in line for line in said) == 1


def test_the_conversion_is_unchanged(monkeypatch):
    frame, _ = _fetch(monkeypatch, _latest(timestamps={"metal": METAL_STAMP}))
    gold = frame[frame["name"] == "gold"].iloc[0]
    assert gold["live_price_usd_per_kg"] == catalog._per_troy_oz_to_per_kg(1923.86)
    assert gold["live_price_source"] == "metals.dev:gold"


def test_the_provider_date_reaches_the_final_table(monkeypatch, tmp_path):
    _fetch(monkeypatch, _latest(timestamps={"metal": METAL_STAMP}))
    cfg = dataclasses.replace(catalog.CONFIG, metals_api_key="OFFLINE",
                              output_dir=str(tmp_path))
    catalog.build_mineral_value_catalog(cfg)
    t = pd.read_csv(tmp_path / cfg.catalog_filename)
    quoted = t[t["live_price_source"].astype(str).str.startswith("metals.dev:")]
    assert len(quoted) > 0
    assert set(quoted["live_price_date"]) == {"2023-07-05"}
    assert set(t["catalog_date"]) != {"2023-07-05"}, "the build keeps its own date"
