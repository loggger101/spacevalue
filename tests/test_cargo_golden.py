# -*- coding: utf-8 -*-
"""economicspace's numbers, held at the seam they cross into this package.

`spacevalue.cargo` decides what an asteroid's hold is worth, and economicspace
argues every release from bit-identical output.  So a change here that moves
one float is a change to its results, whether or not anything here looks
different.  The fixture is a seeded sample of real calls across the seam,
recorded inside economicspace's Stage 4 (calc 1.32.0, before the move) over
thirteen small cells that between them reach every market model, the phase
walk and the four-fraction walk, the detailed and plain phases, the flown and
the deducted refinery, and the surplus wall.  Each call keeps its arguments
before and after (the knapsack spends the `caps` dict it is given) and its
result, every float as `repr`, so the replay compares the last bit.

A failure means a number economicspace publishes moved.  That may be right,
but it is a calc release there, not a tidy-up here: say so in CHANGELOG.md,
and re-record the fixture only together with that release, never to make
this test pass.  The recorder is economicspace's `campaign/cargo_golden.py`
(`record DIR --fixtures FILE`), run on a clean tree at the release that
changed the numbers; the directory name says which calc it was.
"""

import gzip
import json
import os

import pytest

from spacevalue import _cargo_codec
from spacevalue import cargo

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "data", "cargo-calc-1.32.0", "calls.json.gz")

with gzip.open(FIXTURE, "rt", encoding="utf-8") as _f:
    BODY = json.load(_f)
_DECODER = _cargo_codec.Decoder(BODY["blobs"])


def _expand(e, blobs):
    """An encoding with every blob reference replaced by the blob."""
    if isinstance(e, list):
        if len(e) == 2 and e[0] == "ref":
            return _expand(blobs[e[1]], blobs)
        return [_expand(v, blobs) for v in e]
    return e


def _calls(fn):
    return [c for c in BODY["calls"] if c["fn"] == fn]


@pytest.mark.parametrize("fn", BODY["boundary"])
def test_every_recorded_call_gives_the_same_bits(fn):
    calls = _calls(fn)
    enc = _cargo_codec.Encoder()
    differ = []
    for c in calls:
        args = _DECODER.dec(c["args"])
        kwargs = _DECODER.dec(c["kwargs"])
        result = getattr(cargo, fn)(*args, **kwargs)
        got = [enc.enc(result), enc.enc(list(args)), enc.enc(dict(kwargs))]
        want = [c["result"], c["args_after"], c["kwargs_after"]]
        if _expand(got, enc.blobs) != _expand(want, BODY["blobs"]):
            differ.append(c["variant"])
    assert not differ, "%d of %d recorded %s calls changed (cells: %s)" % (
        len(differ), len(calls), fn, ", ".join(sorted(set(differ))))


def test_every_boundary_function_was_recorded():
    """A function with no recorded call is a function this test cannot see."""
    assert all(_calls(fn) for fn in BODY["boundary"])


def test_the_boundary_is_what_economicspace_calls():
    """The recorded functions are the callables of the consumer contract."""
    from test_consumer_contract import CARGO_SURFACE
    callables = [n for n in CARGO_SURFACE if callable(getattr(cargo, n))]
    assert sorted(callables) == sorted(BODY["boundary"])
