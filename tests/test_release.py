# -*- coding: utf-8 -*-
"""A price release, and the gate that decides whether it may be published.

The release is built once per module from the seed snapshot.  Every defect
below is planted on a copy of it, and each must fail `check_release`: a gate
that passes a damaged release is the failure economicspace would inherit,
because it trusts whatever the manifest vouches for.
"""

import json
import os
import shutil

import pytest

import spacevalue
from spacevalue import catalog
from spacevalue.release import ASSET_MANIFEST, build_release, check_release

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "data", "prices-2026-10-07")


@pytest.fixture(scope="module")
def release(tmp_path_factory):
    out = str(tmp_path_factory.mktemp("release"))
    build_release("metals-2026-10-07", out)
    return out


@pytest.fixture
def copy(release, tmp_path):
    dest = str(tmp_path / "copy")
    shutil.copytree(release, dest)
    return dest


def _manifest(d):
    with open(os.path.join(d, ASSET_MANIFEST), encoding="utf-8") as fh:
        return json.load(fh)


def _write_manifest(d, m):
    with open(os.path.join(d, ASSET_MANIFEST), "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=2)


def test_a_fresh_release_passes(release):
    assert check_release(release) == []


def test_the_release_is_tagged_and_dated_by_its_quotes(release):
    m = _manifest(release)
    assert m["release_tag"] == "prices-2026-10-07"
    assert m["catalog_date"] == "2026-10-07"
    assert m["pipeline_version"] == spacevalue.DATA_VERSION
    assert m["package_version"] == spacevalue.__version__
    assert m["quote_snapshot"] == "metals-2026-10-07"
    assert sorted(m["destinations"]) == sorted(catalog.DELIVERY_DESTINATIONS)


def test_the_release_tables_are_the_fixtures(release):
    for d in catalog.DELIVERY_DESTINATIONS:
        name = spacevalue.table_filename(d)
        a = open(os.path.join(release, name), "rb").read()
        b = open(os.path.join(FIXTURES, name), "rb").read()
        assert a == b, name


def test_a_release_is_never_written_over(release):
    with pytest.raises(FileExistsError):
        build_release("metals-2026-10-07", release)


def test_a_release_cannot_be_built_live():
    with pytest.raises((FileNotFoundError, ValueError)):
        build_release("", "unused")


# ---------------------------------------------------------- planted defects
def test_an_edited_table_is_caught(copy):
    p = os.path.join(copy, spacevalue.table_filename("cislunar"))
    data = bytearray(open(p, "rb").read())
    i = data.index(b"water")
    data[i] = ord("W")                            # same length, one byte
    open(p, "wb").write(bytes(data))
    assert any("does not match" in x for x in check_release(copy))


def test_a_missing_table_is_caught(copy):
    os.remove(os.path.join(copy, spacevalue.table_filename("gto")))
    assert any("missing" in x for x in check_release(copy))


def test_a_destination_left_out_is_caught(copy):
    m = _manifest(copy)
    del m["files"][spacevalue.table_filename("geo")]
    _write_manifest(copy, m)
    assert any("no table for geo" in x for x in check_release(copy))


def test_another_data_contract_is_caught(copy):
    m = _manifest(copy)
    m["pipeline_version"] = "1.16.0"
    _write_manifest(copy, m)
    assert any("data contract" in x for x in check_release(copy))


def test_quotes_that_are_not_the_snapshots_are_caught(copy):
    m = _manifest(copy)
    m["quotes"][0]["close"] = repr(float(m["quotes"][0]["close"]) + 1.0)
    _write_manifest(copy, m)
    assert any("not the snapshot" in x for x in check_release(copy))


def test_a_table_rewritten_with_lf_is_caught(copy):
    """Rehashed to match, so only the line-ending rule can see it."""
    import hashlib
    name = spacevalue.table_filename("leo")
    p = os.path.join(copy, name)
    data = open(p, "rb").read().replace(b"\r\n", b"\n")
    open(p, "wb").write(data)
    m = _manifest(copy)
    m["files"][name]["bytes"] = len(data)
    m["files"][name]["sha256"] = hashlib.sha256(data).hexdigest()
    _write_manifest(copy, m)
    assert any("CRLF" in x for x in check_release(copy))


def test_a_blank_price_not_marked_unpriced_is_caught(copy):
    """Rehashed to match, so only the price rule can see it."""
    import hashlib

    import pandas as pd
    name = spacevalue.table_filename("cislunar")
    p = os.path.join(copy, name)
    t = pd.read_csv(p, float_precision="round_trip", keep_default_na=False,
                    dtype=str)
    t.loc[t["name"] == "water", "price_usd_per_kg"] = ""
    t.to_csv(p, index=False, lineterminator="\r\n")
    data = open(p, "rb").read()
    m = _manifest(copy)
    m["files"][name]["bytes"] = len(data)
    m["files"][name]["sha256"] = hashlib.sha256(data).hexdigest()
    _write_manifest(copy, m)
    assert any("not marked unpriced" in x for x in check_release(copy))


def test_no_manifest_is_caught(tmp_path):
    assert check_release(str(tmp_path)) != []
