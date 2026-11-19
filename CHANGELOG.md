# Changelog

Two numbers, and they mean different things:

    pipeline_version        the DATA contract, stamped into every row
    spacevalue.__version__  the PACKAGE release

A change that moves any number a build produces moves the data contract. A
new contract is not evidence that a number moved.

## Data contracts

### 1.22.1 - 2026-11-19

**The destination notes name their sources. No number moves.** The `notes`
route sentences cite the studies behind each figure: the cislunar sum as a
cross-study benchmark (NASA-CR-195527, Benson et al. 2025), the lunar route's
Apollo figures (NASA SP-4029), DRA 5.0's page for the 1-sol orbit with the
200-km comparator called a two-body calculation, and the Mars entry fraction's
MSL and Perseverance ratios (General_Research rc-769 to rc-771). The 28.5 deg
GTO plane is called a reference scenario (rc-604), and the nickel-iron row's
analogue is called analyst-selected (rc-815).

In the re-recorded `tests/data/prices-2026-10-07/` fixtures only `notes` and
the stamp move; every price, yield and value column is identical to 1.22.0.

### 1.22.0 - 2026-11-18

**`ref_price_source` says what each reference price is. No number moves.**
Until now every reference row carried "USGS/LME/mineralogy reference", which
read as a quote for rows that have none (General_Research rc-455, rc-456,
rc-589 to rc-595, rc-621 to rc-623). Now a row with no reference price says
it has no direct quote and is unpriced on the Earth route by design, any
value being its yields at refined-element prices, a gross contained-element
proxy (20 rows: the Fe-Ni alloys, magnetite, chromite, ilmenite, troilite,
schreibersite, the sulfides and the rare PGM phases). The five bulk silicates'
$0.05/kg is labelled an engineering placeholder. Every other row keeps the
series label.

In the `tests/data/prices-2026-10-07/` fixtures, which are re-recorded, only
`ref_price_source` (those 25 rows) and the stamp move; every price, yield and
value column is identical to 1.21.0.

### 1.21.0 - 2026-11-12

**spacecost v0.14.0 → v0.17.1, and the delivery chains move.** Nothing in this
repository's tables changed. The delivery and downleg prices come from spacecost,
and two of its 0.16.0 changes reach them:

- **LOX $0.20 → $0.37/kg** (spacecost rc-185). The tug's fuel costs more, so
  the delivered price of every in-space destination rises: cislunar $7,236.54
  to $7,237 (rounded), lunar surface to $48,227, Mars surface to $186,307. LEO,
  GTO, GEO and Mars orbit round the same.
- **A recovery is one charge per batch** (spacecost rc-254), so every downleg
  falls: 0.02% to GTO, 0.16% LEO, 0.57% cislunar, 1.1% Mars orbit, 1.7% GEO,
  2.7% lunar surface and 4.5% Mars surface.

In the `tests/data/prices-2026-10-07/` fixtures, which are re-recorded, three
columns move: `price_usd_per_kg`, `price_before_processing_usd_per_kg` and
`downleg_cost_usd_per_kg`. Earth surface does not move. Rows used in space
rise by a median of 5e-6 (Mars surface) to 7e-4 (LEO) of their price. Rows
shipped home rise by as much as the downleg fell: up to 12% at GEO, lunar and
Mars surface, where the downleg is large beside the price. At Mars orbit water
and palladium swap places in the table's price order.
The cislunar witness in `test_cargo_market_class.py` follows the shielding
prices: $28,053,387 → $28,054,272 pooled, $32,061,014 → $32,062,025 per name.

### 1.20.0 - 2026-11-10

**The stale static prices are re-reviewed on one date** (General_Research rc-302
to rc-308, rc-313, rc-324, rc-325). Each row now uses the latest figure of a
public series, dated by the new `_REF_PRICE_AUDIT_DATE`, 2026-11-10. Cobalt,
osmium and the bulk rows were not re-reviewed and keep 2026-05-29.

| row | was $/kg | now $/kg | source now |
|---|---:|---:|---|
| nickel | 18.806 | 15.436 | World Bank Pink Sheet, Oct 2026 average |
| copper | 13.543 | 14.508 | World Bank Pink Sheet, Oct 2026 average |
| gold | 145,506 | 130,335.9 | Umicore 10am indication, $4,053.90/oz |
| silver | 2,436.5 | 1,675.1 | Umicore 10am indication, $52.10/oz |
| platinum | 61,472.2 | 50,219.5 | Johnson Matthey base, $1,562/oz |
| palladium | 43,853.6 | 33,629.7 | Johnson Matthey base, $1,046/oz |
| rhodium | 320,000 | 302,217 | Johnson Matthey base, $9,400/oz |
| iridium | 257,206 | 324,722.5 | Johnson Matthey base, $10,100/oz |
| ruthenium | 56,263.8 | 61,086.4 | Johnson Matthey base, $1,900/oz |
| tungsten | 45 | 353.10 | SMM APT, Rotterdam, 2026-11-05, midpoint $2,800/mtu, as contained W |
| iron | 0.319 | 0.319 | kept: USGS 2025 annual is still the latest national figure |

Johnson Matthey and Umicore figures are for 2026-11-10 (Johnson Matthey's in New
York). Gold, silver, platinum and palladium were LBMA prices, but LBMA's daily
prices are no longer public. Umicore's figures are indications, not fixings.
Tungsten keeps its old method, APT per contained kilogram of W, which is not a
refined-metal price.

**In the recorded build, only rows without a quote move.** The
`tests/data/prices-2026-10-07/` fixtures are re-recorded. Gold, silver,
platinum, palladium and copper keep their 2026-09-29 closes, so only their
`ref_price_usd_per_kg` column moved. Iridium, rhodium, ruthenium, nickel and
tungsten are priced off the reference column, so their prices moved at every
destination. Iridium rose 26%, ruthenium 9%, rhodium fell 6% and nickel 18%. On
Earth, tungsten went from $45 to $353.10. Rows priced by their yields did not
move.

### 1.19.0 - 2026-11-04

**One in-space demand class is one market** (rc-261). No price, ceiling or demand
total moves. Every table gains `market_id`, naming the allowance each row spends:
`in-space shielding`, `in-space structural`, `in-space chemical` or
`in-space propellant` for a commodity sold at an in-space destination, and the
commodity's own name for one shipped to Earth or sold at `earth_surface`, whose
world markets stay separate. At cislunar, 59 rows are 20 markets.

`annual_market_kg` gives every row of a class the class's whole share of one
import budget, and each row spent its own copy. 20 t of olivine and pyroxene sold
at full price into a 15 t/yr shielding market, $32.06M; on one allowance at the
default surplus fraction it is 15 t full and 5 t discounted, $28.05M. The
`tests/data/prices-2026-10-07/` fixtures are re-recorded with the column and the
stamp; only those two moved. An already published release is unchanged, reads as
it did, and keeps a market per name; the next `prices-*` release carries this.

### 1.18.0 - 2026-11-04

**A price release moves, and no quoted price does.** Built from the same closes,
the five quoted metals and every price derived from them are unchanged. What
moves is this, from General_Research's candidates, and the eight fixtures in
`tests/data/prices-2026-10-07/` were re-recorded with it. An already published
release is unchanged; the next `prices-*` release carries all of it.

- **Market depth** (`annual_market_kg`, shipped-to-Earth ceilings): osmium 1,000
  to 500 kg/yr (rc-125; the IPA/SFA factsheet, about 500-550 kg/yr over 2024-25),
  gold 3.0e6 to 3.3e6 (rc-147), nickel 3.6e9 to 3.9e9 (rc-148), palladium 2.1e5
  to 1.9e5 (rc-149), platinum 1.8e5 to 1.7e5 (rc-150), copper 2.2e10 to 2.3e10
  (rc-151), each USGS MCS 2026 mine production; chromium 4.4e10 to 4.7e10
  (rc-152) and titanium 3.0e8 to 3.2e8 (rc-153), MCS 2025.
- **Reference prices**: gold 150,000 to 145,506 USD/kg (rc-142) and palladium
  48,000 to 43,853.6 (rc-141), the LBMA prices on the table's own reference date,
  2026-05-29. Both are quoted metals, so a snapshot build does not price from
  them; they are what a build with no quote falls back on.
- **Notes and metadata**: the cited notes of osmium (rc-126), cobalt (rc-143),
  plagioclase (rc-145) and iron (rc-146), pyroxene's formula to
  `(Mg,Fe,Ca)2Si2O6` (rc-242), and the coplanar GTO burn in GEO's destination
  note to 1,477 m/s, so the launch site's latitude costs 359, not 358 (rc-177;
  a comparison, not a term in the price).
- **`live_price_date` on a live metals.dev build** (rc-267): the provider's
  `timestamps.metal` as a UTC day, then a root `timestamp`, then the older `date`
  and `timestamp_iso`. The fetch day was stamped on a quote that did not say
  otherwise, and `timestamps.currency` is never read. A payload with none of
  these leaves the date blank and says so; `catalog_date` stays the build's.

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

### 0.8.6 - 2026-11-19

`spacevalue build` now writes `<table>.manifest.json` beside the CSV: package
version, data contract, catalog date, destination, quote snapshot (or live),
source commit and the CSV's sha256, with `release_tag` null because a
standalone build is not a release (General_Research rc-776). `release` is
unchanged. Data contract unchanged at 1.22.1; no value moves.

### 0.8.5 - 2026-11-19

Comments and CITATIONS.md only; data contract unchanged at 1.22.1. The
carbon-dioxide Earth market ceiling, 230 Mt/yr, is total CO2 use (IEA 2019),
not merchant sales (about 30 Mt/yr, S&P Global 2025), and is no longer
labelled merchant; the owner chose the total-use boundary (General_Research
rc-526). No value moves.

### 0.8.4 - 2026-11-19

Comments and CITATIONS.md only; data contract unchanged at 1.22.1. CITATIONS.md
maps the phase densities to the Handbook of Mineralogy sheets, Remo 1993 and
Agrawal et al. 2016, with Agrawal's troilite printed as FeSi and left
unreconciled (General_Research rc-855, rc-856). The water utility comment no
longer calls electrolysis the only processing step: it names the hydrolox and
resistojet routes, with AQUARIUS and HYDROS-C cited (rc-864). No value moves.

### 0.8.3 - 2026-11-19

Comments only; data contract unchanged at 1.22.1. The four water utility
factors are called scenarios with no destination-matched derivation, and their
linear effect on water's price is stated (General_Research rc-823); the
silicates' composite 0.25 is called a scenario whose non-shielding part no
source quantifies (rc-296). No price, yield or value moves.

### 0.8.2 - 2026-11-19

Comments and CITATIONS.md only; data contract unchanged at 1.22.1. The
nickel-iron PGM split is called analyst-selected, with Wright & Fleischer's
30 ppm siderite total located (p. A1, Table 15) and each named source's
scope stated (General_Research rc-835); Cowen, Agnello & Petit (2012), cited
in `implied_element_value()`, gains a full entry (rc-849). No price, yield
or value moves.

### 0.8.1 - 2026-11-19

Data contract **1.22.0 → 1.22.1**: destination and nickel-iron `notes` only
(see the contract entry above), CITATIONS.md gains the route studies, and
`rust/README.md` calls its speed row an informal timing (General_Research
rc-765). No price, yield or value moves.

### 0.8.0 - 2026-11-18

Data contract **1.21.0 → 1.22.0**: the reference rows' `ref_price_source`
column is now set per row (see the contract entry above), and the fixtures
are re-recorded for that column and the stamp. No price, yield or value
moves. Nothing reaches economicspace until a `prices-*` release is built on
it and Stage 2 repins.

### 0.7.3 - 2026-11-18

Data contract 1.21.0, unchanged, and **no number moves**: comments in
`catalog.py`, CITATIONS.md and `__version__`; `catalog.py` parses to the same
AST. Applies General_Research rc-523, rc-524, rc-527, rc-529 and rc-602, which
ask what each world-production ceiling and the earth-surface water price
stand on.

- Silver's 26,000 t is USGS MCS 2026's 2025e mine output (rc-523).
- Iridium, rhodium and ruthenium have no recorded edition and MCS does not
  report them singly: rounded scenarios, beside Johnson Matthey's 2025
  primary supply (rc-524).
- Sulfur's 83 Mt is not the group's MCS 2025 figure (85 Mt); it sits about
  1% under MCS 2026's 83.9 and 84.0 Mt and is kept (rc-527).
- Elemental phosphorus's 1 Mt is a scenario inside JRC's 900-1,200 kt/yr
  estimate (rc-529).
- The earth-surface water price is a scenario; Omaha MUD's industrial tariff,
  $0.000694/kg at the marginal rate, is one comparator (rc-602).

### 0.7.2 - 2026-11-18

Data contract 1.21.0, unchanged, and **no number moves**: CITATIONS.md, one
comment in `catalog.py` and `__version__`. `catalog.py` parses to the same AST.
Applies General_Research rc-664, rc-787, rc-788, rc-796 and rc-800 to rc-803,
which ask for the full reference behind sources the code already cites.

- The grouped "Comparators beside `IN_SPACE_UTILITY`" paragraph becomes one
  entry per source, with title, authors, report number, NTRS identifier, link
  and the page each comment uses: Roberts et al. 2023 and the ISAM State of
  Play 2026 (p. 266), Kim et al.'s TP-3473 (Fig. 15), Lewis 1992 and Morren et
  al. 1987, the ammonia arcjet and habitat-nitrogen reports, Franco et al.
  2019, Moses & Bushnell 2016, Lewis 2016, Wade 1989, Zeitlin et al. 2015,
  Abney et al. 2026 and Grugel 2008. Each is scoped to the claim beside it.
- Abney et al.'s sulfur-poison statement is on PDF p. 2, not p. 4 as the
  sulfur comment said (rc-802).
- The osmium production row's IPA/SFA factsheet (rc-664) and Howard 2021's
  DSEV comparator beside the `leo` ceiling (rc-788) are listed.

### 0.7.1 - 2026-11-17

Data contract 1.21.0, unchanged, and **no number moves**: nothing under
`spacevalue/` changed except `__version__`. This adds `rust/`, a Rust copy of
`cargo.py`'s knapsack (`optimal_payload_mix`, `_hold_refining`,
`_capped_sale_value`) for economicspace's `es_core` to link, and an optional
binding of it, `spacevalue_cargo_rs`. `spacevalue` never imports either.

- `rust/cargo_core` (plain Rust) is the port; `rust/cargo_py` (PyO3) binds
  it. The binding is a separate package, installed from this tag with
  `pip install "spacevalue_cargo_rs @ git+https://github.com/loggger101/spacevalue@v0.7.1#subdirectory=rust/cargo_py"`
  (it needs a Rust toolchain). It is not a `spacevalue` extra, which would
  make every install of the package need one.
- `tests/test_cargo_rust.py` holds the binding to the Python bit for bit
  (the golden replay, and fuzzed calls with exceptions compared); it skips
  without the binding unless `SPACEVALUE_REQUIRE_RUST=1`.
- CI's new `rust` job, on the three hosts and Python 3.13 and 3.14: the
  planted build (`planted_knapsack_defect`) failing all six Rust tests, the
  good binding installed as a consumer installs it, and the whole suite with
  it. A knapsack change made only in `cargo.py` now fails here. There is no
  `cargo test` step: `cargo_core` has no Rust tests, only the comparison with
  `cargo.py` through the binding.

### 0.7.0 - 2026-11-12

Data contract **1.21.0**, above: spacecost is pinned at `v0.17.1`, was
`v0.14.0`, and its delivery chains move every in-space price and every downleg.
The fixtures, the README's delivered prices and the cargo witness are
re-recorded with it. No code here changed. economicspace sees this once it
repins this tag and a `prices-*` release built from it.

### 0.6.2 - 2026-11-12

Data contract 1.20.0, unchanged: comments, one `cargo.py` docstring and this
file only, and **no number moves**. `catalog.py` parses to an identical AST,
and `cargo.py` differs only in that docstring. Thirty-three General_Research
citation candidates. Each asked for the basis of a judgement value. None found
a like-for-like source, so each comment now says the value is a scenario and
names the nearest comparator.

- **In-space utility** (rc-424 to rc-431, rc-447, rc-450, rc-454, rc-472,
  rc-473, rc-483): structural metals beside NASA's in-space metals maturity
  and ESA MELT; the volatiles and chemicals beside arcjet, habitat-nitrogen,
  Sabatier and CELSS figures; the detailed phases called inherited proxies.
- **Demand shares** (rc-432): no source splits an import budget by class.
- **Processing energy** (rc-434, rc-437 to rc-443, rc-452, rc-453): each row
  an engineering scenario per kg of raw feed, beside its nearest comparator.
- **Energy cost** (rc-482): the 15 years assume full output; cost scales as
  1/availability.
- **Reference rows** (rc-508 to rc-513): carbon, organics, spinel,
  phyllosilicates and oxides prices are scenario anchors; cohenite is valued
  as Fe and Ni only; the native-PGM and awaruite yields are scenarios.
- **`saturation_price_multiplier`** (rc-507): ε is the caller's scenario; no
  PGM demand elasticity is measured.

Not here: rc-455 and rc-456 change the published `ref_price_source` label,
which moves the data contract; rc-433 is a value and rc-484 a new routing
method.

### 0.6.1 - 2026-11-10

Data contract 1.20.0, unchanged: comments and this file only, and **no number
moves**. Three General_Research judgement candidates. Each value stays, and
its comment now names the comparator that questions it.

- **`geo` 44,600 kg/yr** (rc-290): the 613-payload count stays as dated
  (GCAT, Jan 2026). In Nov 2026 the count is 585 or 602 in CelesTrak, by rule,
  and 524 in GCAT, so no catalog-and-rule pair is chosen yet.
- **`leo` 500,000 kg/yr** (rc-381): NASA's DSEV Mars concept annualises to
  1,404 t/yr, one architecture's modelled capacity, not a market.
- **Silicate utility 0.25** (rc-296): a composite of shielding, feedstock and
  market judgement. As shielding alone, regolith is within ~1.2x of water
  (NASA TP-3473 Fig. 15), so the 4:1 gap is not shielding physics.

### 0.6.0 - 2026-11-10

Data contract **1.20.0**, above: the static prices are refreshed, and
economicspace sees none of this until it repins. The release also cites sources
for eight General_Research citation candidates. Those values stay, and each
comment now says what kind of number it is and what it can be compared with.

- **Processing energies.** Iron-family 5.0 kWh/kg sits beside hydrogen DRI's
  3.48 (rc-366), and titanium's 20 beside FFC's measured 17–21.5 (rc-389).
  Silicates' 1.0 is a low-energy scenario: sintering lunar simulants took
  19–27 kWh/kg (rc-390). Phosphorus's 8.0 sits beside the P4 furnace's 14
  (rc-394). Carbonates' ~0.5 kWh/kg is calcination's theoretical minimum, not
  a kiln's measured use (rc-395).
- **Demand ceilings.** `gto` is an idealised scenario, since its three sources
  are not one cohort (rc-393). `mars_orbit` and `mars_surface` cite NASA's
  notional "100s" and "10's" of t/yr as order-of-magnitude anchors, with the
  values unchanged (rc-391, rc-392).

### 0.5.0 - 2026-11-05

Data contract 1.19.0, unchanged: **no number moves**, and `tests/test_cargo_golden.py`
holds. economicspace sees none of this until it repins.

- **`sold_as_is(mineral_df, phases=None)`** (rc-279, the spacevalue half). With
  the refinery flown, `_phase_terms` picks a route on Stage 2's net prices, whose
  fixed deduction stands in for a plant the mission then really pays for, so a
  mission search never sees the other route. This returns a copy of the table
  whose phases sell as they are, for a consumer to evaluate beside the original
  and keep the better mission on its own objective. On the LEO fixture magnetite
  goes from refined to as-is, at a lower price and a lower energy. The original
  table keeps its route. economicspace's search of the two is not built: it needs
  this release pinned, which needs a `prices-*` release at this contract.

### 0.4.0 - 2026-11-04

Data contract 1.19.0, above. economicspace sees none of this until it repins,
and the shared markets need a `prices-*` release at that contract as well.

- **`phase_market_key` reads the table's `market_id`**, through `market_table`,
  which now returns a `MarketTable`: the same dict, with `.ids` beside it. Every
  consumer that already pools on the key pools by class without changing.
- **A pooled allowance goes to the dearer phase first** in `_capped_sale_value`.
  The allowance is settled ahead of the sum, and the sum keeps its order, so a
  sale nothing pools gives the same bits. `optimal_payload_mix` needed no change:
  its walk is already in price order, and its result matched an independent
  linear program on 6,000 random loads with shared allowances, ties and tiers.
- **A body with no named fraction is all residual** (rc-263). The residual floor
  required some named mass, so a wholly Unknown composition was worth 0 while a
  silicate fraction of 1e-12 earned the whole floor. `asteroid_bulk_value_usd_per_kg`,
  `asteroid_phase_table` and `asteroid_best_phase_usd_per_kg` now give it the
  bulk-silicate quote, as one phase carrying the silicates ceiling. A negative
  sum, a malformed row, is unchanged, and a value is not a measurement: Unknown
  stays Unknown, and a body with no mass or density is still declined.

### 0.3.0 - 2026-11-04

Data contract 1.18.0, above. Besides that:

- `spacevalue check-release` holds a release to its snapshot, not just to its
  own checksums. Every quote the manifest declares must match the snapshot in
  all five fields, each once and in any order, where it compared a set of ticker
  and close (rc-276). Every quoted metal must appear once, with its quote's
  source and date and the price its close implies, and carry the price
  `in_space_price_usd_per_kg` gives it, where it counted five non-blank sources
  (rc-277). No frozen snapshot changed.
- `asteroid_refinery`'s composition memo works (rc-243). The loop over phases
  overwrote the composition key with a phase name, so the memo was never filled,
  and a composition `_composition_key` declines reached the write with nothing
  bound. **No float moves**: `tests/test_cargo_golden.py` holds unchanged.
- `mineral_to_element_value` and `_mineral_implied_value` say what they assume:
  refined metal at refined prices, with no payable fraction, treatment or
  refining charge (rc-121). The value is unchanged.

### 0.2.0 - 2026-10-26

economicspace's cargo valuation moves here, and no number moves: no price,
and none of economicspace's results. The data contract stays 1.17.0, since a
price build is untouched.

- `spacevalue.cargo`: what a hold of asteroid ore is worth and how much a
  market takes. The mineral and phase walk, the inseparable phases, the flown
  refinery, the composition memo, the market ceilings and the payload knapsack,
  moved from economicspace's Stage 4 (`modules/calc.py`, calc 1.32.0)
  VERBATIM: the module's body is byte-identical to calc's span, comments
  included, and every definition's AST is unchanged. The market-model names
  and their validator stay in calc, which owns the config they validate.
- `import spacevalue` no longer imports the catalog or spacecost: every public
  name resolves on first use (PEP 562). A Stage 4 worker imports
  `spacevalue.cargo` at spawn, and it imports nothing else from here.
- `tests/test_cargo_golden.py` replays a seeded sample of real calls across
  that seam, recorded in calc 1.32.0 over thirteen cells that reach every
  market model and every phase and refinery path, and demands the same bits.
  A failure there is a change to economicspace's results. On the recording
  host (Windows) every call is held to the bit; macOS's C library rounds `pow`
  differently, and two elasticity-multiplier calls come out one ulp away, so
  off that host the one function that calls `pow` is held to one ulp and
  everything else still to the bit (Linux matches Windows exactly). Its codec ships as
  `spacevalue._cargo_codec`, so economicspace's recorder
  (`campaign/cargo_golden.py`) and this test share one copy.
- The consumer contract names the twenty-five `spacevalue.cargo` names calc
  imports.
- README: a "What a row holds" section naming the columns most readers want,
  held to the fixture's header by `tests/test_docs.py`, and how to read a
  release's CSV with pandas without installing anything.
- pyproject: the Python versions CI runs, an Issues link, and economicspace's
  link no longer labelled "Upstream", since it is the consumer.

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
- Requires Python 3.12. Before 3.12, `sum()` over floats was not compensated,
  and the iron yields of taenite and tetrataenite, which are sums, came out one
  bit different; CI found it on its 3.9 legs. The tables are the 3.12+ answer,
  which is the one economicspace measured on.
- The proof: built from `metals-2026-10-07`, all eight destinations equal
  economicspace's mineral_value 1.16.0 fed the same closes, and the seven it
  froze at 1.15.0 match those files byte for byte once the stamp is swapped.
  The eight tables are committed in `tests/data/prices-2026-10-07/` and
  rebuilt by the suite.
