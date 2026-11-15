# -*- coding: utf-8 -*-
"""PROTOTYPE: the Rust knapsack (`spacevalue_cargo_rs`) gives the Python's bits.

The optional extension built from `rust/cargo_py` re-implements three
functions of `spacevalue.cargo`: `optimal_payload_mix`, `_hold_refining` and
`_capped_sale_value`.  Its contract is the golden test's: the same result,
float for float, and the same arguments afterwards (the knapsack spends the
`caps` dict it is given).  Two checks hold it there:

  * every recorded call in the golden fixture, replayed through the
    extension and compared exactly as `test_cargo_golden.py` compares the
    Python (the same encoder, so the last bit);
  * a seeded fuzz against the Python itself, aimed at what a port gets wrong:
    price ties (the sort must be stable), negative and zero prices, duplicate
    phase names, `None` caps values, markets shared through `cap_keys`, the
    surplus tier at, below and above 1.0, int arguments, infinities.

The extension is optional, so without it these tests skip, which would make
them a check that never runs: `SPACEVALUE_REQUIRE_RUST=1` turns the skip into
a failure, and the gate (`rust/cargo_py/README.md`) always sets it.  A build
with the `planted_knapsack_defect` feature must FAIL here; the gate proves it.
"""

import copy
import gzip
import json
import math
import os
import random

import pytest

from spacevalue import _cargo_codec
from spacevalue import cargo

try:
    import spacevalue_cargo_rs as rs
except ImportError:  # pragma: no cover - exercised only without the build
    rs = None
    if os.environ.get("SPACEVALUE_REQUIRE_RUST") == "1":
        raise

pytestmark = pytest.mark.skipif(rs is None, reason="spacevalue_cargo_rs not built")

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "data", "cargo-calc-1.32.0", "calls.json.gz")
PORTED = ("optimal_payload_mix", "_hold_refining", "_capped_sale_value")


def _expand(e, blobs):
    if isinstance(e, list):
        if len(e) == 2 and e[0] == "ref":
            return _expand(blobs[e[1]], blobs)
        return [_expand(v, blobs) for v in e]
    return e


@pytest.mark.parametrize("fn", PORTED)
def test_rust_replays_every_recorded_call(fn):
    with gzip.open(FIXTURE, "rt", encoding="utf-8") as f:
        body = json.load(f)
    dec = _cargo_codec.Decoder(body["blobs"])
    calls = [c for c in body["calls"] if c["fn"] == fn]
    assert calls
    enc = _cargo_codec.Encoder()
    fast0, slow0 = rs.counts()
    differ = []
    for c in calls:
        args = dec.dec(c["args"])
        kwargs = dec.dec(c["kwargs"])
        result = getattr(rs, fn)(*args, **kwargs)
        got = [enc.enc(result), enc.enc(list(args)), enc.enc(dict(kwargs))]
        want = [c["result"], c["args_after"], c["kwargs_after"]]
        if _expand(got, enc.blobs) != _expand(want, body["blobs"]):
            differ.append(c["variant"])
    fast, slow = rs.counts()
    assert not differ, "%d of %d %s calls differ (cells: %s)" % (
        len(differ), len(calls), fn, ", ".join(sorted(set(differ))))
    # A replay the extension handed back to the Python proves nothing.
    assert fast - fast0 >= 0.9 * len(calls), (fn, fast - fast0, slow - slow0)


# ── fuzz ────────────────────────────────────────────────────────────────────

NAMES = ["water", "kamacite", "taenite", "olivine", "pyroxene", "troilite",
         "silicates", "other (bulk silicate)", "carbon", "pgm"]
PRICES = [0.0, -0.0, 0.05, 1.0, 2.5, 2.5, 12.0, 1500.0, -3.0, 40000.0]


def _float(r, scale):
    k = r.random()
    if k < 0.08:
        return 0.0
    if k < 0.12:
        return float(r.choice([1, 2, 7]))
    if k < 0.14:
        return math.inf
    return r.random() * scale


def _phases(r):
    n = r.choice([0, 1, 2, 3, 4, 6, 8, 10])
    pool = NAMES[:]
    out = []
    for _ in range(n):
        name = r.choice(NAMES) if r.random() < 0.1 else (pool.pop(r.randrange(len(pool))) if pool else "x")
        frac = r.choice([0.0, 0.5, 1e-9]) if r.random() < 0.15 else r.random()
        price = r.choice(PRICES) if r.random() < 0.5 else r.uniform(-5, 5000)
        out.append((name, frac, price))
    return out


def _caps(r, phases):
    if r.random() < 0.4:
        return None, None
    caps = {}
    keys = {}
    for name, _f, _p in phases:
        if r.random() < 0.3:
            keys[name] = r.choice(["silicates", "metals", name])
    for key in set(keys.values()) | {p[0] for p in phases}:
        k = r.random()
        if k < 0.1:
            caps[key] = None
        elif k < 0.2:
            caps[key] = 0.0
        elif k < 0.3:
            continue
        else:
            caps[key] = r.random() * 2000
    if r.random() < 0.2:
        keys = {}
    elif r.random() < 0.2:
        keys = None
    return caps, keys


def _payload(r):
    k = r.random()
    if k < 0.05:
        return 0.0
    if k < 0.08:
        return -1.0
    if k < 0.12:
        return r.choice([500, 1000])
    if k < 0.13:
        return math.inf
    return r.random() * 5000


def _same(a, b):
    enc = _cargo_codec.Encoder()
    return _expand(enc.enc(a), enc.blobs) == _expand(enc.enc(b), enc.blobs)


def _call(f, *a, **kw):
    """The result, or the exception's type and text: the port must raise
    where the Python raises, and the same thing."""
    try:
        return ("ok", f(*a, **kw))
    except Exception as e:  # noqa: BLE001 - compared, not swallowed
        return ("raised", type(e).__name__, str(e))


def test_rust_mix_matches_python_on_hostile_inputs():
    r = random.Random(20261115)
    differ = []
    for i in range(60000):
        phases = _phases(r)
        caps, keys = _caps(r, phases)
        kw = {}
        if r.random() < 0.3:
            kw["want_phase"] = r.choice(["water"] + [p[0] for p in phases] if phases else ["water"])
        if caps is not None:
            kw["caps"] = caps
            if keys is not None:
                kw["cap_keys"] = keys
        if r.random() < 0.6:
            kw["surplus_price_frac"] = r.choice([0.0, 0.5, 1.0, 1.5, r.random()])
        args = (_payload(r), _float(r, 20000) if r.random() < 0.9 else r.choice([3000, 0]),
                phases, r.choice([0.9, 1.0, r.random()]))
        kw_py, kw_rs = copy.deepcopy(kw), copy.deepcopy(kw)
        want = _call(cargo.optimal_payload_mix, *copy.deepcopy(args), **kw_py)
        got = _call(rs.optimal_payload_mix, *copy.deepcopy(args), **kw_rs)
        if not (_same(want, got) and _same(kw_py, kw_rs)):
            differ.append((i, args, kw))
    assert not differ, "%d differ; first %r" % (len(differ), differ[0])
    fast, slow = rs.counts()
    assert fast > slow


def test_rust_hold_refining_matches_python():
    r = random.Random(7)
    differ = []
    for i in range(30000):
        phases = _phases(r)
        if r.random() < 0.1:
            phases = None
        refinery = None
        if r.random() < 0.85:
            per = {p[0]: r.random() * 50 for p in (phases or []) if r.random() < 0.8}
            refinery = (per, r.random() * 30)
        args = (refinery, phases, _payload(r), _float(r, 20000), r.random() < 0.7,
                r.choice([0.9, 1.0, r.random()]))
        want = _call(cargo._hold_refining, *copy.deepcopy(args))
        got = _call(rs._hold_refining, *copy.deepcopy(args))
        if not _same(want, got):
            differ.append((i, args))
    assert not differ, "%d differ; first %r" % (len(differ), differ[0])


def test_rust_capped_sale_matches_python():
    r = random.Random(11)
    differ = []
    for i in range(30000):
        terms = []
        for _ in range(r.choice([0, 1, 2, 4, 7])):
            terms.append((_float(r, 3000), r.choice(PRICES) if r.random() < 0.5 else r.uniform(-5, 5000),
                          _float(r, 500), r.choice(["silicates", "metals", "water", "pgm"])))
        args = [terms, r.choice([0.0, 0.25, 1.0, r.random() * 10])]
        if r.random() < 0.6:
            args.append(r.choice([0.0, 0.5, 1.0, r.random()]))
        want = _call(cargo._capped_sale_value, *copy.deepcopy(args))
        got = _call(rs._capped_sale_value, *copy.deepcopy(args))
        if not _same(want, got):
            differ.append((i, args))
    assert not differ, "%d differ; first %r" % (len(differ), differ[0])
