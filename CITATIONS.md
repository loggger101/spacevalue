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
  and copper reference prices, October 2026 averages from the November 2026
  edition (data contract 1.20.0; May 2026 averages from mineral_value 1.13.0).
- **Johnson Matthey base prices**, New York, 2026-11-10: the platinum,
  palladium, rhodium, iridium and ruthenium reference prices (data contract
  1.20.0; iridium and ruthenium were from JM's *PGM Market Report*, May 2026).
  JM's terms reserve its price data, so each row quotes the figure and its
  date, and this repository carries no copy.
- **Umicore Precious Metals Management, 10am indicative prices**, 2026-11-10:
  the gold and silver reference prices (data contract 1.20.0). These are
  indications, not fixings.
- **LBMA precious-metal prices**: the gold, silver, platinum and palladium
  reference prices until data contract 1.20.0 (the 2026-05-29 prices). LBMA no
  longer publishes its daily prices openly.
- **Shanghai Metals Market (SMM)**, tungsten APT, CIF Rotterdam, 2026-11-05:
  the tungsten reference price as contained W (data contract 1.20.0).
- **SteelBenchmarker**, price history, 2026-10-28: an East-of-Mississippi No. 1
  HMS comparator beside the iron row. The value is not taken from it.

The **quote snapshots** in `spacevalue/quotes/` are Yahoo Finance closes of
COMEX and NYMEX front-month futures (GC=F, SI=F, PL=F, PA=F, HG=F), recorded
on the date each file is named for. `metals-2026-10-07` was not recorded at
the time: it holds the closes recovered exactly from economicspace's Stage 2
tables of that date, and its `note` column says so.

A price is a price **on a date**. Every row carries `catalog_date`, the
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
- **McDowell, *Space Activities in 2025***, Table 14(e) (34 GTO launches);
  **Toson et al. 2016**, IAC-16-C4.6.9 (a ~6 t chemical GEO platform); and
  **Byers 1989**, NASA TM-103174 (apogee propellant 40–50% of GTO mass): the
  `gto` ceiling's arithmetic, an idealised scenario since the three are not
  shown to describe one cohort (General_Research rc-393).
- **Sanders, G. B. & Kleinhenz, J. E. 2024**, NASA JSC presentation, NTRS
  20240002713, p. 3: "100s" of t/yr for human Mars transportation and "10's"
  of t/yr of commodities for initial commercial use, a notional unfunded
  scale beside the `mars_orbit` and `mars_surface` ceilings (rc-391, rc-392).

## In-space processing energy

Comparators beside `IN_SPACE_PROCESSING_KWH_PER_KG`, whose rows stay
engineering allowances; none has the same feed and product boundary.

- **Vogl, V., Åhman, M. & Nilsson, L. J. 2018**, J. Clean. Prod. 203, 736:
  hydrogen direct reduction, 3.48 kWh/kg liquid steel (iron family, rc-366).
- **Hu, D., Dolganov, A., et al. 2018**, JOM 70, 129: FFC-Cambridge, 21.5
  kWh/kg Ti, ~17 with an inert anode (titanium, rc-389).
- **Liu et al. 2025**, J. Eur. Ceram. Soc. 45, 117047: microwave sintering of
  lunar simulants, 69–98 MJ/kg (silicates, rc-390).
- **Matos, C. T., et al. 2021**, JRC EUR 30704 EN, p. 30: up to 14 kWh/kg of
  elemental P4 (phosphorus, rc-394).
- **McMillan, C., et al. 2016**, NREL/TP-6A50-66763, Appendix N: calcination's
  theoretical minimum 3.18 GJ/t CaO (~0.5 kWh/kg CaCO3) and measured kiln use
  (carbonates, rc-395).
- **Comparators named in 0.6.2's comments** (General_Research rc-434 to
  rc-453): Paz 2023, NTRS 20230005189 (water's boundary); NASA-CR-171982
  (ilmenite reduction to O2); Bleiwas, USGS OFR 2011-1253, Tables 19 and 35
  (chromium electrolysis, phosphate-rock grinding); Li et al. 2014, J. Air
  Waste Manag. Assoc. 64, 95 (sulfur distillation); Gull, Feng & Pasek
  2022, Life 12, 1591 (schreibersite corrosion).

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
- **Comparators beside `IN_SPACE_UTILITY`, every factor an engineering
  scenario** (rc-424 to rc-483): Roberts et al. 2023 (NASA in-space metals
  TMP) and NASA's ISAM State of Play 2026, p. 266; JPL Pub 90-4 and NASA
  TM-89876 (ammonia arcjets); ICES-2026-238 (habitat nitrogen); NASA
  TM-100113 (resistojet fluids); ICES-2019-077 (Sabatier); NASA CR-4229 and
  NTRS 20160006646 (phosphorus); ICES-2026-601 (sulfur as a catalyst
  poison); Lewis, NASA SP-509, and Lewis's NIAC report NNX15AL85G;
  Moses & Bushnell, NASA/TM-2016-219182; Grugel, NASA/TM-2008-215250.
- **Beside the demand shares and prices**: Kornuta et al. 2019 and LunA-10
  (rc-432); USGS MCS 2025 amorphous graphite and Platts N330 carbon black
  (rc-508); Cabri, Harris & Weiser 1996 (native PGM, rc-512); Kutyrev et
  al. 2023, Lithosphere 2023(1):126 (awaruite, rc-513); IMF WP 2024/077 and
  Banque de France Eco Notepad 419 (elasticity, rc-507).

## Software

- **spacecost** (MIT, the same author): the delivery chains, the launch price
  and the quote-snapshot code. Pinned to a tagged release in `pyproject.toml`.
- **numpy** and **pandas** (BSD-3-Clause). **yfinance** (Apache-2.0) and
  **requests** (Apache-2.0) only for live quotes.

## Citing this package

Cite the release you used, by its tag (`prices-YYYY-MM-DD` for the tables,
`vX.Y.Z` for the code), and the data contract stamped in its rows.
