# -*- coding: utf-8 -*-
"""The recorded metal quotes, and a table priced from them.

The snapshot code is spacecost's (`spacecost.quotes`), tested there.  What is
tested here is this package's use of it: the committed metal snapshots match
their checksums, the seed is the five closes economicspace's tables recorded,
a recorded build is the build those closes would have made live, and a build
that asks for both live and recorded quotes is refused.
"""

import dataclasses
import sys
import types

import pandas as pd
import pytest

from spacecost import quotes
from spacevalue import catalog

SEED = "metals-2026-10-07"


def test_every_committed_metal_snapshot_matches_its_checksum():
    assert quotes.check_snapshots(catalog.QUOTES_DIR) == []


def test_every_snapshot_quotes_every_ticker_a_row_reads():
    for name in quotes.list_snapshots(catalog.QUOTES_DIR):
        rows = quotes.load_snapshot(name, catalog.QUOTES_DIR)
        assert quotes.missing(rows, catalog.metal_tickers()) == [], name


def test_the_tickers_are_the_five_comex_and_nymex_metals():
    assert catalog.metal_tickers() == {
        "GC=F": "troy_oz", "SI=F": "troy_oz", "PL=F": "troy_oz",
        "PA=F": "troy_oz", "HG=F": "lb"}


def test_the_seed_holds_the_closes_economicspace_recorded():
    rows = quotes.closes_by_ticker(quotes.load_snapshot(SEED, catalog.QUOTES_DIR))
    assert {t: q.close for t, q in rows.items()} == {
        "GC=F": 4175.2998046875, "PL=F": 1713.4000244140625, "PA=F": 1212.5,
        "HG=F": 6.6479997634887695, "SI=F": 61.2599983215332}


class _Ticker(object):
    def __init__(self, symbol):
        self.symbol = symbol

    def history(self, period=None, auto_adjust=None):
        q = quotes.closes_by_ticker(
            quotes.load_snapshot(SEED, catalog.QUOTES_DIR))[self.symbol]
        return pd.DataFrame({"Close": [q.close]},
                            index=pd.to_datetime([q.close_date]))


def test_a_recorded_build_is_the_live_build_of_the_same_closes(monkeypatch):
    module = types.ModuleType("yfinance")
    module.Ticker = _Ticker
    monkeypatch.setitem(sys.modules, "yfinance", module)
    live = catalog.fetch_yfinance(dataclasses.replace(catalog.CONFIG,
                                                      use_yfinance=True))
    recorded = catalog.snapshot_metal_prices(
        dataclasses.replace(catalog.CONFIG, quote_snapshot=SEED))
    pd.testing.assert_frame_equal(live, recorded, check_exact=True)


def test_live_and_recorded_together_are_refused(tmp_path):
    cfg = dataclasses.replace(catalog.CONFIG, use_yfinance=True,
                              quote_snapshot=SEED, output_dir=str(tmp_path))
    with pytest.raises(ValueError, match="not both"):
        catalog.build_mineral_value_catalog(cfg)


def test_a_snapshot_missing_a_metal_is_refused(tmp_path, monkeypatch):
    rows = [q for q in quotes.load_snapshot(SEED, catalog.QUOTES_DIR)
            if q.ticker != "PA=F"]
    quotes.write_snapshot("metals-2026-10-08", rows, str(tmp_path))
    monkeypatch.setattr(catalog, "QUOTES_DIR", str(tmp_path))
    with pytest.raises(ValueError, match="no PA=F quote"):
        catalog.load_metal_snapshot("metals-2026-10-08")


def test_metals_dev_is_not_consulted_in_a_recorded_build(tmp_path, monkeypatch):
    called = []
    monkeypatch.setattr(catalog, "fetch_metals_dev",
                        lambda c: called.append(c) or pd.DataFrame())
    cfg = dataclasses.replace(catalog.CONFIG, quote_snapshot=SEED,
                              metals_api_key="a-real-key",
                              output_dir=str(tmp_path))
    catalog.build_mineral_value_catalog(cfg)
    assert called == []


def test_the_default_build_needs_no_network(tmp_path, monkeypatch):
    """Off by default: nothing reaches yfinance unless asked."""
    monkeypatch.setitem(sys.modules, "yfinance", None)    # import would fail
    cfg = dataclasses.replace(catalog.CONFIG, output_dir=str(tmp_path),
                              use_metals_api=False)
    t = catalog.build_mineral_value_catalog(cfg)
    assert t["live_price_source"].isna().all()
