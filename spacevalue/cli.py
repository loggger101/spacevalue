# -*- coding: utf-8 -*-
"""Command line: `spacevalue` or `python -m spacevalue`.

    spacevalue show cislunar --quotes metals-2026-10-07
                                        one destination's table, printed
    spacevalue build cislunar --quotes metals-2026-10-07 -o out/
                                        write one destination's table
    spacevalue build cislunar --live    the same from today's closes
    spacevalue release --quotes metals-2026-10-07 -o dist/
                                        every destination, plus manifest.json
    spacevalue check-release dist/      the gate a release must pass
    spacevalue quotes list              the recorded metal snapshots
    spacevalue quotes check             hold each one to SHA256SUMS
    spacevalue quotes record            record the last finished closes

`build`, `release` and `quotes record` are the only commands that write.
Printed text is ASCII, because Windows gives a redirected stdout cp1252 and
one non-ASCII character there kills the run.
"""

import argparse
import dataclasses
import os
import sys

from spacecost import quotes as _quotes
from spacecost import set_verbose

from . import __version__
from . import catalog as _catalog
from .release import build_release, check_release

_PREVIEW = ["name", "kind", "price_usd_per_kg", "price_basis", "value_route",
            "live_price_source", "annual_market_kg"]


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="spacevalue",
        description="What a kilogram of asteroid material is worth, and where.")
    p.add_argument("--version", action="version",
                   version="spacevalue %s (data contract %s)"
                   % (__version__, _catalog.CONFIG.pipeline_version))
    sub = p.add_subparsers(dest="command", required=True)
    dests = list(_catalog.DELIVERY_DESTINATIONS)

    for name, helptext in (("show", "print one destination's table"),
                           ("build", "write one destination's table")):
        c = sub.add_parser(name, help=helptext)
        c.add_argument("destination", choices=dests)
        src = c.add_mutually_exclusive_group()
        src.add_argument("--quotes", default="", metavar="SNAPSHOT",
                         help="price metals from a recorded snapshot")
        src.add_argument("--live", action="store_true",
                         help="fetch today's closes (needs spacevalue[live])")
        if name == "build":
            c.add_argument("-o", "--output-dir", default="",
                           help="where to write (default: "
                                "$SPACEVALUE_OUTPUT_DIR, else ./spacevalue_data)")
            c.add_argument("-q", "--quiet", action="store_true")
        else:
            c.add_argument("-n", "--rows", type=int, default=0,
                           help="only the first N rows")

    r = sub.add_parser("release", help="every destination's table from one "
                                       "snapshot, plus manifest.json")
    r.add_argument("--quotes", required=True, metavar="SNAPSHOT")
    r.add_argument("-o", "--output-dir", required=True)
    r.add_argument("--tag", default=None,
                   help="release tag (default: prices-<recorded date>)")

    k = sub.add_parser("check-release", help="the gate a release must pass")
    k.add_argument("directory")

    q = sub.add_parser("quotes", help="the recorded metal-quote snapshots")
    qa = q.add_subparsers(dest="action", required=True)
    qa.add_parser("list", help="name every snapshot, oldest first")
    qa.add_parser("check", help="hold every snapshot to SHA256SUMS")
    qa.add_parser("record", help="fetch the last finished close of each "
                                 "metal ticker and write a new snapshot")
    return p


def _config(args, **extra):
    return dataclasses.replace(
        _catalog.CONFIG, delivery_destination=args.destination,
        quote_snapshot=args.quotes, use_yfinance=args.live, **extra)


def main(argv=None) -> int:
    """Entry point.  Returns a process exit code."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    args = _parser().parse_args(argv)

    if args.command == "show":
        # Built into a scratch directory: `show` writes nothing you keep.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            table = _catalog.build_mineral_value_catalog(
                _config(args, output_dir=tmp))
        cols = [c for c in _PREVIEW if c in table.columns]
        if args.rows:
            table = table.head(args.rows)
        print(table[cols].to_string(index=False))
        return 0

    if args.command == "build":
        set_verbose(not args.quiet)
        cfg = _config(args, output_dir=args.output_dir)
        _catalog.build_mineral_value_catalog(cfg)
        if args.quiet:
            print(os.path.join(cfg.resolved_output_dir(), cfg.catalog_filename))
        return 0

    if args.command == "release":
        set_verbose(True)
        manifest = build_release(args.quotes, args.output_dir, tag=args.tag)
        bad = check_release(args.output_dir)
        for line in bad:
            print("FAIL  " + line)
        if not bad:
            print("OK  %s: %d tables, data contract %s, quotes %s"
                  % (manifest["release_tag"], len(manifest["files"]),
                     manifest["pipeline_version"], manifest["quote_snapshot"]))
        return 1 if bad else 0

    if args.command == "check-release":
        bad = check_release(args.directory)
        for line in bad:
            print("FAIL  " + line)
        if not bad:
            print("OK  %s passes" % args.directory)
        return 1 if bad else 0

    if args.command == "quotes":
        if args.action == "list":
            for name in _quotes.list_snapshots(_catalog.QUOTES_DIR):
                rows = _quotes.load_snapshot(name, _catalog.QUOTES_DIR)
                print("%-22s %s" % (name, " ".join(
                    "%s=%r" % (q.ticker, q.close) for q in rows)))
            return 0
        if args.action == "check":
            bad = _quotes.check_snapshots(_catalog.QUOTES_DIR)
            for line in bad:
                print("FAIL  " + line)
            if not bad:
                print("OK  %d snapshot(s) match %s" % (
                    len(_quotes.list_snapshots(_catalog.QUOTES_DIR)),
                    _quotes.SUMS_FILE))
            return 1 if bad else 0
        set_verbose(True)
        path = _quotes.record_snapshot("metals", _catalog.metal_tickers(),
                                       _catalog.QUOTES_DIR)
        print("wrote " + path)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
