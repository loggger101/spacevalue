# -*- coding: utf-8 -*-
"""A price release: every destination's table from one snapshot, and a manifest.

A release is what economicspace installs as its Stage 2, the way it installs a
published asteroid catalog as its Stage 1: it downloads the manifest, refuses
a data contract it was not written against, downloads the table for its
destination, and checks every byte against the manifest's sha256 before
anything on disk changes.  It never prices anything itself.

    spacevalue release --quotes metals-2026-10-07 -o dist/

writes into `dist/`:

    mineral_value_catalog.<destination>.csv   one per destination, CRLF
    manifest.json                             tag, contract, quotes, sha256s

A release is built only from a recorded snapshot, never from live quotes,
so anyone holding this package at the same tag can rebuild it and get the
same bytes.  The tag is `prices-<recorded date>` unless one is given.

`check_release` is the gate the publish workflow runs before anything is
uploaded, and it is what the tests plant defects against.  It reads only what
is on disk, and fails on anything a consumer would otherwise take on trust.
"""

import dataclasses
import hashlib
import json
import math
import os
import platform
import subprocess
from typing import Dict, List, Optional

import pandas as pd

import spacecost
from spacecost import quotes as _quotes
from spacecost import say

from . import catalog as _catalog

ASSET_MANIFEST = "manifest.json"
MANIFEST_VERSION = 1


def table_filename(destination: str) -> str:
    """The asset name of one destination's table."""
    return "mineral_value_catalog.%s.csv" % destination


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _source_commit() -> str:
    """The commit this package was built from, or "" outside a checkout."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=here,
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def build_release(snapshot: str, out_dir: str,
                  tag: Optional[str] = None) -> dict:
    """Build every destination's table from `snapshot` and write the manifest.

    Returns the manifest.  Refuses to write into a directory that already
    holds a release, because a half-replaced one would carry two snapshots
    under one manifest.
    """
    from . import __version__

    rows = _catalog.load_metal_snapshot(snapshot)
    recorded = _quotes.recorded_date(rows)
    tag = tag or "prices-%s" % recorded
    os.makedirs(out_dir, exist_ok=True)
    if os.path.exists(os.path.join(out_dir, ASSET_MANIFEST)):
        raise FileExistsError("%s already holds a release" % out_dir)

    files: Dict[str, dict] = {}
    for dest in _catalog.DELIVERY_DESTINATIONS:
        cfg = dataclasses.replace(
            _catalog.CONFIG, delivery_destination=dest,
            quote_snapshot=snapshot, use_yfinance=False, output_dir=out_dir,
            catalog_filename=table_filename(dest))
        table = _catalog.build_mineral_value_catalog(cfg)
        path = os.path.join(out_dir, cfg.catalog_filename)
        files[cfg.catalog_filename] = {
            "destination": dest,
            "rows": int(len(table)),
            "bytes": os.path.getsize(path),
            "sha256": _sha256(path),
        }
        say("  %-36s %s" % (cfg.catalog_filename, files[cfg.catalog_filename]["sha256"][:16]))

    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "release_tag": tag,
        "catalog_date": recorded,
        "pipeline_version": _catalog.CONFIG.pipeline_version,
        "package_version": __version__,
        "spacecost_version": spacecost.__version__,
        "source_commit": _source_commit(),
        "quote_snapshot": snapshot,
        "quotes": [
            {"ticker": q.ticker, "source": q.source, "close": repr(q.close),
             "unit": q.unit, "close_date": q.close_date}
            for q in sorted(rows, key=lambda q: q.ticker)
        ],
        "destinations": list(_catalog.DELIVERY_DESTINATIONS),
        "built_on": {
            "python": platform.python_version(),
            "system": platform.system(),
            "machine": platform.machine(),
            "numpy": __import__("numpy").__version__,
            "pandas": pd.__version__,
        },
        "files": files,
    }
    path = os.path.join(out_dir, ASSET_MANIFEST)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    return manifest


def check_release(out_dir: str) -> List[str]:
    """Everything wrong with the release in `out_dir`; [] means publishable.

    Reads the manifest and every table it names, and holds each table to the
    manifest, to the package that wrote it, and to the snapshot it names.
    """
    path = os.path.join(out_dir, ASSET_MANIFEST)
    if not os.path.exists(path):
        return ["no %s in %s" % (ASSET_MANIFEST, out_dir)]
    with open(path, encoding="utf-8") as fh:
        m = json.load(fh)

    bad = []
    contract = _catalog.CONFIG.pipeline_version
    if m.get("manifest_version") != MANIFEST_VERSION:
        bad.append("manifest_version is %r" % m.get("manifest_version"))
    if m.get("pipeline_version") != contract:
        bad.append("manifest says data contract %s, this package writes %s"
                   % (m.get("pipeline_version"), contract))
    want = set(_catalog.DELIVERY_DESTINATIONS)
    if set(m.get("destinations", [])) != want:
        bad.append("destinations %s, expected %s"
                   % (sorted(m.get("destinations", [])), sorted(want)))
    files = m.get("files", {})
    named = {e.get("destination") for e in files.values()}
    for dest in sorted(want - named):
        bad.append("no table for %s" % dest)

    # The quotes the manifest records must be the snapshot's, exactly.
    try:
        snap = _catalog.load_metal_snapshot(m.get("quote_snapshot", ""))
    except (OSError, ValueError) as exc:
        bad.append("snapshot %r: %s" % (m.get("quote_snapshot"), exc))
        snap = []
    if snap:
        recorded = _quotes.recorded_date(snap)
        if m.get("catalog_date") != recorded:
            bad.append("catalog_date %s, but the snapshot was recorded %s"
                       % (m.get("catalog_date"), recorded))
        listed = {(q["ticker"], q["close"]) for q in m.get("quotes", [])}
        if listed != {(q.ticker, repr(q.close)) for q in snap}:
            bad.append("the manifest's quotes are not the snapshot's")

    n_reference = len(_catalog.MINERAL_REFERENCE)
    n_quoted = len(_catalog.metal_tickers())
    for fname, entry in sorted(files.items()):
        p = os.path.join(out_dir, fname)
        dest = entry.get("destination")
        if fname != table_filename(dest or ""):
            bad.append("%s is listed for destination %r" % (fname, dest))
        if not os.path.exists(p):
            bad.append("%s is listed and missing" % fname)
            continue
        if os.path.getsize(p) != entry.get("bytes") or _sha256(p) != entry.get("sha256"):
            bad.append("%s does not match its manifest entry" % fname)
            continue
        with open(p, "rb") as fh:
            raw = fh.read()
        if raw.count(b"\n") != raw.count(b"\r\n"):
            bad.append("%s is not CRLF throughout" % fname)
        # The default parser: the gate tests signs, blanks and counts, never
        # the last bit of a float, so it needs no exact read.
        t = pd.read_csv(p)
        if len(t) != entry.get("rows") or len(t) != n_reference:
            bad.append("%s has %d rows; the manifest says %s and the reference "
                       "table has %d" % (fname, len(t), entry.get("rows"),
                                         n_reference))
        for col, expect in (("pipeline_version", contract),
                            ("catalog_date", m.get("catalog_date")),
                            ("delivery_destination", dest)):
            got = sorted(set(t[col].astype(str))) if col in t.columns else []
            if got != [str(expect)]:
                bad.append("%s: %s is %s, expected %s" % (fname, col, got, expect))
        # A blank price is legitimate only where the row says so: a mineral
        # with no market of its own at Earth's surface is valued through its
        # yields, and the table marks it "unpriced".  Any other price must be
        # a finite number at or above zero (zero is the freight floor).
        prices = pd.to_numeric(t["price_usd_per_kg"], errors="coerce")
        blank = prices.isna()
        if (t.loc[blank, "price_basis"] != "unpriced").any():
            bad.append("%s has a blank price on a row not marked unpriced"
                       % fname)
        if not all(math.isfinite(v) and v >= 0 for v in prices[~blank]):
            bad.append("%s has a price that is not a finite number >= 0" % fname)
        quoted = int(t["live_price_source"].notna().sum())
        if quoted != n_quoted:
            bad.append("%s prices %d rows from quotes; the snapshot quotes %d"
                       % (fname, quoted, n_quoted))
    return bad
