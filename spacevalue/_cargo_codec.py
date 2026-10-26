# -*- coding: utf-8 -*-
"""Exact, type-keeping JSON for the values that cross spacevalue.cargo's seam.

Every float is written as `repr`, which round-trips the last bit, and keeps
its type (a numpy float64 decodes as a numpy float64), because the type of an
argument can decide the type of a result.  Dicts keep their insertion order:
the payload walk iterates them.  Big things (catalog rows, DataFrames) go into
a blob table once and are referenced, and a blob decodes to ONE object per
replay, because the module memoises on the mineral table's identity.

Not part of the pricing.  It ships in the package so the two ends of one
fixture share one codec: economicspace's `campaign/cargo_golden.py` records
calls with `Encoder` inside a Stage 4 run, and `tests/test_cargo_golden.py`
replays them here with `Decoder`.  Nothing in `cargo` imports it.
"""
import hashlib
import json

import numpy as np
import pandas as pd

BLOB_MIN_CHARS = 1500


def _ftype(x):
    return type(x).__name__


class Encoder(object):
    """Encode values, collecting large containers into `self.blobs`."""

    def __init__(self, blobs=None):
        self.blobs = {} if blobs is None else blobs
        self._ids = {}

    def _blob(self, tagged):
        text = json.dumps(tagged, separators=(",", ":"))
        if len(text) < BLOB_MIN_CHARS:
            return tagged
        key = hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]
        self.blobs.setdefault(key, tagged)
        return ["ref", key]

    def enc(self, x):
        if x is None:
            return None
        if isinstance(x, (bool, np.bool_)):
            return ["b", bool(x), _ftype(x)]
        if isinstance(x, (int, np.integer)):
            return ["i", int(x), _ftype(x)]
        if isinstance(x, (float, np.floating)):
            return ["f", repr(float(x)), _ftype(x)]
        if isinstance(x, str):
            return ["s", str(x)]
        if isinstance(x, tuple):
            return ["t", [self.enc(v) for v in x]]
        if isinstance(x, list):
            return self._blob(["l", [self.enc(v) for v in x]])
        if isinstance(x, dict):
            return self._blob(["d", [[self.enc(k), self.enc(v)]
                                     for k, v in x.items()]])
        if isinstance(x, (set, frozenset)):
            items = sorted((self.enc(v) for v in x),
                           key=lambda e: json.dumps(e))
            return ["S" if isinstance(x, set) else "F", items]
        if isinstance(x, pd.DataFrame):
            hit = self._ids.get(id(x))
            if hit is not None and hit[0] is x:
                return hit[1]
            cols =[[self.enc(c), str(x[c].dtype),
                     [self.enc(v) for v in x[c].tolist()]]
                    for c in x.columns]
            body = ["D", cols, [self.enc(i) for i in x.index.tolist()]]
            text = json.dumps(body, separators=(",", ":"))
            key = hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]
            self.blobs.setdefault(key, body)
            # The model never mutates its mineral table, so one encoding per
            # object is safe; the object is held so its id cannot be reused.
            self._ids[id(x)] = (x, ["ref", key])
            return ["ref", key]
        if isinstance(x, pd.Series):
            return self._blob(["R", str(x.dtype), x.name if isinstance(x.name, str) else None,
                               [[self.enc(k), self.enc(v)] for k, v in x.items()]])
        raise TypeError("cargo_codec cannot encode %s" % type(x).__name__)


_NP_SCALARS = {"float64": np.float64, "float32": np.float32,
               "int64": np.int64, "int32": np.int32, "bool_": np.bool_,
               "bool": None, "float": None, "int": None}


class Decoder(object):
    """Decode values; each blob decodes once and is shared thereafter."""

    def __init__(self, blobs):
        self.blobs = blobs
        self.memo = {}

    def dec(self, e):
        if e is None:
            return None
        tag = e[0]
        if tag == "ref":
            key = e[1]
            if key not in self.memo:
                self.memo[key] = self.dec(self.blobs[key])
            return self.memo[key]
        if tag == "b":
            t = _NP_SCALARS.get(e[2])
            return t(e[1]) if t else bool(e[1])
        if tag == "i":
            t = _NP_SCALARS.get(e[2])
            return t(e[1]) if t else int(e[1])
        if tag == "f":
            v = float(e[1])
            t = _NP_SCALARS.get(e[2])
            return t(v) if t else v
        if tag == "s":
            return e[1]
        if tag == "t":
            return tuple(self.dec(v) for v in e[1])
        if tag == "l":
            return [self.dec(v) for v in e[1]]
        if tag == "d":
            return {self.dec(k): self.dec(v) for k, v in e[1]}
        if tag == "S":
            return set(self.dec(v) for v in e[1])
        if tag == "F":
            return frozenset(self.dec(v) for v in e[1])
        if tag == "D":
            data = {}
            for c, dtype, vals in e[1]:
                values = [self.dec(v) for v in vals]
                try:
                    data[self.dec(c)] = pd.Series(values, dtype=dtype)
                except (TypeError, ValueError):
                    data[self.dec(c)] = pd.Series(values, dtype=object)
            df = pd.DataFrame(data)
            df.index = [self.dec(i) for i in e[2]]
            return df
        if tag == "R":
            items = [(self.dec(k), self.dec(v)) for k, v in e[3]]
            try:
                return pd.Series(dict(items), dtype=e[1], name=e[2])
            except (TypeError, ValueError):
                return pd.Series(dict(items), dtype=object, name=e[2])
        raise ValueError("unknown tag %r" % (tag,))
