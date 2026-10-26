# Changelog

Two numbers, and they mean different things:

    pipeline_version        the DATA contract, stamped into every row
    spacevalue.__version__  the PACKAGE release

A change that moves any number a build produces moves the data contract. A
new contract is not evidence that a number moved.

## Data contracts

### 1.17.0 - 2026-10-26

**No number moved.** Built from the same closes, every table is the one data
contract 1.16.0 wrote, apart from the stamp. What changed is where prices can
come from and what a table's date means:

- `quote_snapshot` prices the metals from a recorded snapshot in
  `spacevalue/quotes/`, and a table built from one is dated by the day its
  quotes were recorded (`catalog_date`), not the day it was built.
- `use_yfinance` defaults to False: a build with no snapshot prices the five
  quoted metals at their reference rows and touches no network.
- metals.dev is not consulted in a recorded build, even with a key.

1.16.0 and every contract before it are economicspace's: its versions.md,
"Stage 2 changelog", is the record, and this repository's git history is the
code.

## Package releases

### 0.1.0 - 2026-10-26

The first release, split out of economicspace, where this was Stage 2
(`modules/mineral_value.py`). The file's history comes with it.

- `spacevalue.catalog`: the reference table, the eight destinations, in-space
  utility and demand, and `build_mineral_value_catalog`, which writes one
  destination's table.
- `spacevalue.release`: `build_release` writes all eight from one snapshot
  plus `manifest.json`; `check_release` is the gate a release must pass before
  it is published.
- Two metal snapshots: `metals-2026-10-07`, the closes recovered exactly from
  economicspace's tables of that date, and `metals-2026-10-26`, the first
  recorded at the time (the closes of 2026-10-23).
- The command line: `show`, `build`, `release`, `check-release`, and
  `quotes list|check|record`.
- No longer at import: installing packages, printing, creating a directory,
  a global warnings filter, pandas display options.
- Depends on spacecost v0.14.0, which carries the delivery chains, the launch
  price and the snapshot code (`spacecost.quotes`).
- The proof: built from `metals-2026-10-07`, all eight destinations equal
  economicspace's mineral_value 1.16.0 fed the same closes, and the seven it
  froze at 1.15.0 match those files byte for byte once the stamp is swapped.
  The eight tables are committed in `tests/data/prices-2026-10-07/` and
  rebuilt by the suite.
