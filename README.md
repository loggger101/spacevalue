# spacevalue

What a kilogram of asteroid material is worth, and where it is sold. For each
of eight places you could deliver it, a table of every mineral and element an
asteroid composition can name, with its density, what it yields when refined,
and its price there.

The place matters more than the material. Platinum sells for tens of
thousands of dollars a kilogram on Earth, but nobody at a fuel depot in lunar
orbit wants it, so there it is worth only what it fetches flown home, less the
trip. Water is worth a tenth of a cent on Earth and thousands of dollars in
orbit, because every kilogram already up there is a kilogram nobody has to
launch.

```bash
pip install git+https://github.com/loggger101/spacevalue@v0.1.0
```

```python
import spacevalue

cfg = spacevalue.MineralValueConfig(delivery_destination="cislunar",
                                    quote_snapshot="metals-2026-10-07")
table = spacevalue.build_mineral_value_catalog(cfg)   # also writes the CSV
table[["name", "price_usd_per_kg", "value_route"]].head()
```

```bash
spacevalue show cislunar --quotes metals-2026-10-07 -n 10
spacevalue build leo --quotes metals-2026-10-07 -o out/
spacevalue release --quotes metals-2026-10-07 -o dist/   # all eight + manifest
spacevalue quotes list
```

Or skip the code and download a table: every
[release](https://github.com/loggger101/spacevalue/releases) tagged
`prices-YYYY-MM-DD` carries all eight as CSVs.

## Contents

- [The eight destinations](#the-eight-destinations)
- [How a price is made](#how-a-price-is-made)
- [Prices come from recorded quotes](#prices-come-from-recorded-quotes)
- [Price releases](#price-releases)
- [Two version numbers](#two-version-numbers)
- [The judgement in it](#the-judgement-in-it)
- [Layout](#layout)
- [Where it came from](#where-it-came-from)
- [Citations and licence](#citations-and-licence)

## The eight destinations

What one kilogram already at each place saves its buyer, which is the launch
it replaces. These are derived, not typed: [spacecost](https://github.com/loggger101/spacecost)
flies a kilogram from LEO through each destination's chain of burns, on the
cheapest LEO price a buyer can book, and adds the stages the chain throws away.

| destination | launch cost avoided, $/kg | what gets you there from LEO |
|---|---:|---|
| `earth_surface` | 0 | nothing: it is sold at its terrestrial price |
| `leo` | 2,555 | the launch itself |
| `gto` | 5,168 | 2,455 m/s |
| `geo` | 8,462 | 4,291 m/s |
| `cislunar` | 7,236 | 3,600 m/s to a lunar-vicinity depot (NRHO) |
| `lunar_surface` | 48,226 | 6,100 m/s, all of it propulsive |
| `mars_orbit` | 9,154 | 4,500 m/s to a 1-sol staging orbit |
| `mars_surface` | 186,306 | 4,400 m/s plus aeroentry |

The two surface figures are lower bounds: industrial-scale marginal transport
with no development cost and no cadence limit. Real lunar delivery today costs
far more. `tests/test_docs.py` holds this table to the code.

## How a price is made

At Earth's surface a commodity is worth its market price. Anywhere else it is
worth the better of two fates:

- **used there**: the launch cost avoided, times how good a substitute it is
  for the same mass launched from Earth (its *in-space utility*, 0 to 1), less
  what it costs to process on site; or
- **shipped home**: its Earth price, less the cost of the trip down.

Every row says which fate won (`value_route`) and, at a depot, how much of it
the market there can absorb in a year (`annual_market_kg`). A commodity flown
home is bounded by world production; one sold at a depot by that depot's
import budget, split across commodity classes.

A mineral is priced through what it yields when refined: nickel-iron through
its iron, nickel, cobalt, platinum-group and trace metals, troilite through
its iron and sulfur. The yields are in `yields_json` on every row.

## Prices come from recorded quotes

Five metals have a traded future: gold, silver, platinum, palladium and copper.
Everything else is priced from a reference row stamped with the date it was
last reviewed (USGS, LME, LBMA, the World Bank, Johnson Matthey).

Live quotes make a table that is right on the day and impossible to rebuild the
day after. So the closes are recorded once and committed as a snapshot in
`spacevalue/quotes/`, and a build that names one gives the same bytes on every
run, on any day, offline:

```bash
spacevalue quotes record     # last finished close of each future
spacevalue quotes check      # every snapshot against SHA256SUMS
```

A snapshot holds the close as the exchange quoted it (per troy ounce, per
pound), written so it reads back as the same float. It is never edited:
`SHA256SUMS` records each file, and a changed byte fails the check. A newer
price is a new file. The table's `catalog_date` is the day the quotes were
recorded, not the day you built it.

`metals-2026-10-07` is the exception that proves the format. Nobody recorded
those closes at the time; economicspace's tables of that date kept only the
converted $/kg. Each of the five converts back to exactly one close that
reproduces it bit for bit, so that is what the snapshot holds, and its `note`
column says where it came from.

Live prices are still there, opt-in, for anyone who wants today's and accepts
that it cannot be repeated: `use_yfinance=True` or `spacevalue build --live`,
with the extra `pip install "spacevalue[live] @ git+https://github.com/loggger101/spacevalue@v0.1.0"`.
Asking for live and recorded quotes at once is refused.

The snapshot code is [spacecost's](https://github.com/loggger101/spacecost)
(`spacecost.quotes`), which records its fuel quotes the same way.

## Price releases

A release is the eight tables built from one snapshot, plus a `manifest.json`
naming the tag, the data contract, the snapshot and its quotes, and every
file's size and sha256. It is built only from a recorded snapshot, so anyone
holding this package at the same tag can rebuild it and get the same bytes.

The publish workflow builds it on Windows, runs `spacevalue check-release`,
and uploads nothing unless the gate passes. The gate checks:

- every destination has a table, and every byte matches the manifest
- the manifest's quotes are the snapshot's, and its date is the snapshot's
- every table is CRLF, has one row per reference entry, and carries one data
  contract, one date and its own destination
- a blank price appears only on a row marked `unpriced`
- every quoted metal is priced from its quote

A release is never overwritten. economicspace installs one as its Stage 2, the
same way it installs a published asteroid catalog as its Stage 1: it pins a
tag, refuses a data contract it was not written against, and checks every byte
before anything on disk changes.

The in-space prices pass through the rocket equation and so through the C
library's `exp`, which is not promised to round the last bit the same way on
every platform. The tables are committed in `tests/data/` as written on
Windows, and the test suite rebuilds them on Windows, Linux and macOS.

## Two version numbers

- **The data contract**, `MineralValueConfig.pipeline_version`, currently
  `1.17.0`. Stamped into every row. It moves when a change moves any number a
  build produces, and its history is economicspace's Stage 2 changelog up to
  1.16.0 and [CHANGELOG.md](CHANGELOG.md) from there.
- **The package**, `spacevalue.__version__`. It moves for anything else.

The rule is one-directional: a changed number means a new contract, and a new
contract does not mean a number changed.

## The judgement in it

Some of this is measurement and some is not, and the difference matters.

The launch cost avoided is derived from the rocket equation and a real launch
price. The **in-space utility factors** are engineering judgement: no market
exists yet to calibrate them against. They are the softest input in the
package, kept in one table (`IN_SPACE_UTILITY`) so they can be read and argued
with as a set. Per-destination overrides only ever lower a factor, because a
base that can dig something up locally will not pay to import it; Mars orbit
takes the base profile on purpose, since the Martian crust is 4,100 m/s of
ascent away.

The demand ceilings at a depot are sourced where a source exists (the GEO
ceiling counts the active geostationary satellites) and are estimates
elsewhere, with the published lunar propellant forecasts recorded beside the
cislunar and lunar ones as anchors rather than used as values. A commodity with no in-space market is not worthless at a depot: it
is worth its Earth price less the trip home.

## Layout

```
spacevalue/
    catalog.py      the reference table, the destinations, utility, demand,
                    and the build
    release.py      a release: every destination, the manifest, the gate
    cli.py          `spacevalue`
    quotes/         the metal snapshots and SHA256SUMS, shipped in the wheel
tests/
    data/           the seed release's eight tables, the history they hold
```

## Where it came from

This was Stage 2 of [economicspace](https://github.com/loggger101/economicspace),
an asteroid-mining profitability pipeline, as `modules/mineral_value.py`. Its
git history came with it. The split changed no number: built from
`metals-2026-10-07`, all eight destinations equal economicspace's last Stage 2
(data contract 1.16.0) fed the same closes, and the seven destinations it had
frozen at 1.15.0 match those files byte for byte apart from the stamp.

What changed on the way out: it no longer installs packages, prints, or makes
a directory when imported; live quotes are off by default; output goes to
`./spacevalue_data` or `$SPACEVALUE_OUTPUT_DIR`; and a build can name a
recorded snapshot.

## Citations and licence

MIT; see [LICENSE](LICENSE). Every source behind every row is in
[CITATIONS.md](CITATIONS.md), and a row's own `notes` field is the authority
for its number. Johnson Matthey reserves its price data, so the two rows that
use it quote the figure and the report, and nothing here copies it.
