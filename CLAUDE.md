# CLAUDE.md: working in this repo

spacevalue prices asteroid material at eight destinations. `spacevalue/catalog.py`
is the model (reference table, destinations, utility, demand, the build),
`release.py` the published releases and their gate, `cli.py` the command line,
and `spacevalue/quotes/` the recorded metal quotes. Rules:

- **Changing any number a build produces moves the data contract**
  (`MineralValueConfig.pipeline_version`), with a CHANGELOG entry under "Data
  contracts". A new contract does not mean a number moved. The package version
  (`spacevalue.__version__`, written once; pyproject reads it) is separate.
- **The fixtures are history.** `tests/data/prices-2026-10-07/` is what
  economicspace measured on. A change that moves them is a model change: say so,
  move the contract, and re-record them in the same commit. Never re-record to
  make a test pass.
- **A snapshot is never edited.** A newer quote is a new file, written with
  `spacevalue quotes record`. `SHA256SUMS` holds every file, and the CSVs are
  CRLF by rule (`.gitattributes`), because that is what the sums hash.
- **The judgement tables are judgement.** `IN_SPACE_UTILITY` and its overrides
  are engineering estimates. Overrides only run downward; `mars_orbit`'s empty
  override is deliberate (README, "The judgement in it"); `gto` takes `geo`'s
  profile by reference (asserted). `_UTILITY_FAMILIES` holds each family at
  one level at every destination (asserted). Every commodity needs a
  `_COMMODITY_CLASS` entry (asserted at import), and every in-space
  destination a demand row: a missing row once meant an unbounded market.
- **A price used in space is the Earth price PLUS** `in_space_utility x` the
  launch cost avoided, less processing (`in_space_price_usd_per_kg`). Never
  replace the Earth price with the launch cost: v1.3.0 did, and threw the
  material away. Shipped home it is the Earth price less the downleg, so a
  commodity no depot wants is still worth something there.
- **`annual_market_kg` is routed**: world production bounds a commodity flown
  home, the depot's import budget one sold there. `_DEMAND_SHARE_BY_CLASS`
  splits that budget; its bulk classes sum to 1 (asserted) and `trace` sits on
  top of them.
- **The library is quiet.** No printing, installing or directory creation at
  import; progress goes through spacecost's `say()`. Printed strings are ASCII
  (Windows gives a redirected stdout cp1252). `tests/test_rules.py` holds both.
- **No network by default.** `use_yfinance` is off; a release is built only
  from a recorded snapshot. `metals.dev` is never consulted in a recorded build.
- **economicspace reads names from here** (`tests/test_consumer_contract.py`).
  Removing one is a breaking change: bump the minor version, note it, and edit
  economicspace's `modules/mineral_value.py` in the same breath.
- **spacecost is pinned by tag** in `pyproject.toml`. A spacecost release that
  moves a delivery price moves every in-space price here: re-run the suite at
  the new pin before repinning, and expect the fixtures to move.
- **Releases:** run the "publish prices" workflow with a committed snapshot.
  It builds on Windows, gates with `check-release`, and never overwrites a tag.
  Package releases are tagged `vX.Y.Z` from main; price releases `prices-<date>`.
  Never name a branch like a tag (pip resolves the branch).
- The tree lives in OneDrive. `*-DESKTOP-*` files are sync-conflict copies:
  diff, then delete; never commit one. Never `git stash`. `.githooks/` is
  samebytes' stat-cache hook (`core.hooksPath .githooks`).
