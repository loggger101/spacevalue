# Citations

Where each source behind this package's numbers came from, and what it asks of
anyone who uses them. The authority for a value is the row that carries it, in
`spacevalue/catalog.py`, whose `notes` say which source and which figure; this
file is the list of sources, not a second copy of the values.

The "mineral_value x.y.z" and "master vX.Y.Z" tags say which economicspace
release added a source, because this package was that project's Stage 2 until
its data contract 1.16.0 and its history comes with it. The rc- numbers are
revision candidates in [General_Research](https://github.com/loggger101/General_Research),
where the full texts or their key tables are kept.

## Commodity prices

- **yfinance** (Yahoo Finance): live futures for the metals that trade as
  futures contracts.
- **USGS Mineral Commodity Summaries** and **LME reference prices**: the
  curated fallback table for metals yfinance does not expose. Cited per row in
  `spacevalue/catalog.py`.
- **metals.dev**: optional, off by default. The key defaults to `"DEMO"`, which
  skips the fetcher.
- **U.S. Geological Survey, *Mineral Commodity Summaries 2025*** (published
  2025-01-31): the order of the 2024 prices and world production behind the
  rows mineral_value 1.11.0 added (sulfur, chromium, titanium, gallium,
  germanium, rhenium, tungsten, molybdenum, ammonia). Approximate, and dated
  to the publication rather than to a quote. Phosphorus and CO2 are trade
  prices USGS does not carry; their rows say so.
- **U.S. Geological Survey, *Mineral Commodity Summaries 2026***: the iron row
  (No. 1 heavy melting steel scrap composite, 2025 average), the tungsten note
  (Rotterdam APT during 2025) and cobalt's world mine production (mineral_value
  1.12.3 and 1.13.0); the comments beside the carbonates price (crushed stone,
  average unit value 2025e) and iron's world pig-iron production
  (General_Research rc-144, rc-154).
- **World Bank, *Commodity Markets (Pink Sheet)* monthly prices**: the nickel
  and copper reference prices, May 2026 averages (mineral_value 1.13.0).
- **LBMA precious-metal prices**: the silver and platinum reference prices,
  the fixings on 2026-05-29 (mineral_value 1.13.0).
- **Johnson Matthey, *PGM Market Report* (May 2026)**: the iridium and
  ruthenium reference prices, its Q1-2026 base prices (mineral_value 1.13.0).
  JM's terms reserve its price data, so the row quotes the figure and the
  report, and this repository carries no copy.

The **quote snapshots** in `spacevalue/quotes/` are Yahoo Finance closes of
COMEX and NYMEX front-month futures (GC=F, SI=F, PL=F, PA=F, HG=F), recorded
on the date each file is named for. `metals-2026-10-07` was not recorded at
the time: it holds the closes recovered exactly from economicspace's Stage 2
tables of that date, and its `note` column says so.

⚠️  A price is a price **on a date**. Every row carries `catalog_date`, the
day its quotes were recorded, and `ref_price_date` for its reference figure;
quote them with it.

## In-space demand

- **McDowell, J., *Space Activities in 2025*** (General Catalog of Artificial
  Space Objects, Rev 1.2), Table 22: the count of active geostationary
  payloads behind the `geo` absorption ceiling (mineral_value 1.13.0).
- **Kornuta et al. 2019**, *Commercial Lunar Propellant Architecture* (REACH
  13:100026), and **Northrop Grumman 2024**, *DARPA LunA-10 Lunar Rail Network
  study*: lunar propellant demand forecasts recorded beside the cislunar and
  lunar-surface ceilings as anchors, not used as values (master v1.45.0).

## Mineral composition and densities

- **Densities and formulas**: standard mineralogy references, Klein, C. &
  Hurlbut, C. S., *Manual of Mineralogy*, with Mindat.org and Webmineral.com.
  Bulk physical constants; they do not change between builds.
- **The mineral phases** in each taxonomy class (catalog data contract 1.7.0)
  come from AsteroidCatalog's `asteroid_catalog/mineralogy.py`, which cites a
  meteorite analogue per class (Dunn et al. 2010; King et al. 2015; Howard et
  al. 2015; Alexander et al. 2007; Mittlefehldt 2015; Sunshine et al. 2008;
  Rubin et al. 2019; Hiroi et al. 2001). That repository is the authority for
  them and is not restated here.
- **The trace metals of meteoritic Fe-Ni** in the `nickel-iron` yields (Cu,
  Ga, Ge, Mo, W, Re) are order-of-magnitude means over the common iron
  meteorite groups: Scott, E. R. D. & Wasson, J. T. (1975), *Classification
  and properties of iron meteorites*, Rev. Geophys. Space Phys. 13, 527.

## Facts the comments state

Cited in code comments beside a value they explain; none reaches a value.

- **NASA NSSDCA, *Mars Fact Sheet***,
  <https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html>: the CO2 and
  N2 fractions and surface pressure behind `mars_surface`'s utility comments in
  `spacevalue/catalog.py` (General_Research rc-165).

## Software

- **spacecost** (MIT, the same author): the delivery chains, the launch price
  and the quote-snapshot code. Pinned to a tagged release in `pyproject.toml`.
- **numpy** and **pandas** (BSD-3-Clause). **yfinance** (Apache-2.0) and
  **requests** (Apache-2.0) only for live quotes.

## Citing this package

Cite the release you used, by its tag (`prices-YYYY-MM-DD` for the tables,
`vX.Y.Z` for the code), and the data contract stamped in its rows.
