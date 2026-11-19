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
- **SFA (Oxford) for the International Platinum Group Metals Association,
  *PGM Fact Sheet: Osmium*** (written 19 March 2026; IPA edition May 2026),
  <https://ipa-news.com/assets/pdfs/factsheets/2026-05-ipa-osmium-factsheet.pdf>:
  PDF p. 10, world production "about 500kg-550kg/annum over 2024 and 2025",
  the osmium row of `ANNUAL_WORLD_PRODUCTION_KG` (5.0e2, the low end); and
  the $300–400/oz band beside the osmium reference price (General_Research
  rc-125, rc-664).
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
- **Howard, R. L. 2021**, *A Common Habitat Deep Space Exploration Vehicle for
  Transit and Orbital Operations*, AIAA ASCEND 2021, NASA NTRS 20210021084,
  <https://ntrs.nasa.gov/citations/20210021084>, pp. 4 and 13: 1,404 t/yr of
  LEO propellant transfer, one architecture's modelled capacity beside the
  `leo` ceiling. The 500,000 kg/yr ceiling is a scenario and is not taken
  from it (General_Research rc-788).

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
- **The platinum-group metals of meteoritic Fe-Ni** in the `nickel-iron`
  yields (Pt 15, Pd 10, Ru 3, Ir 4, Os 2, Rh 1.5 and Au 1 ppm) are
  analyst-selected: no table or sample set gives the split (General_Research
  rc-835). The sources named beside them, and what each supports:
  - Wright, T. L. & Fleischer, M. (1965), *Geochemistry of the platinum
    metals*, U.S. Geological Survey Bulletin 1214-A,
    <https://doi.org/10.3133/b1214A>: siderites average 30 ppm total
    platinum metals (p. A1), with per-element ranges in Table 15 (p. A17).
  - Nichiporuk, W. & Brown, H. (1965), *The distribution of platinum and
    palladium metals in iron meteorites and in the metal phase of ordinary
    chondrites*, J. Geophys. Res. 70, 459-470,
    <https://doi.org/10.1029/JZ070i002p00459>: Pt and Pd in iron
    meteorites, among the data Wright & Fleischer summarise; not read here.
  - Lodders, K. (2003), *Solar System Abundances and Condensation
    Temperatures of the Elements*, ApJ 591, 1220-1247,
    <https://doi.org/10.1086/375492>; and Walker, R. J. (2012), *Evidence for
    homogeneous distribution of osmium in the protosolar nebula*, Earth
    Planet. Sci. Lett. 351-352, 36-44,
    <https://doi.org/10.1016/j.epsl.2012.07.026>: named for average
    chondritic and iron-meteorite compositions; neither is the table
    behind the yields.
  - Kargel, J. S. (1994), *Metalliferous asteroids as potential sources of
    precious metals*, J. Geophys. Res. Planets 99(E10), 21129-21141,
    <https://doi.org/10.1029/94JE02141>: LL-chondrite metal at 50-220 ppm
    precious metals, the comparison beside the S-type's ~48 ppm; a
    comparator, not a yield.
- **The trace metals of meteoritic Fe-Ni** in the `nickel-iron` yields (Cu,
  Ga, Ge, Mo, W, Re) are order-of-magnitude means over the common iron
  meteorite groups: Scott, E. R. D. & Wasson, J. T. (1975), *Classification
  and properties of iron meteorites*, Rev. Geophys. Space Phys. 13, 527.

## Concentrate terms

- **Cowen, Agnello & Petit (2012)**, *Evaluation of net smelter returns in
  the South African PGE industry by application of base metal concentrate
  commercial treatment terms*, SAIMM Platinum 2012 conference proceedings,
  pp. 577-592, <https://saimm.co.za/Conferences/Pt2012/577-592_Cowen.pdf>,
  Table IV, p. 585: payability of about 90% for the PGE and 85% for Ni and
  Cu, less treatment and refining charges. Cited in
  `implied_element_value()`'s caveat that refined-metal prices overstate
  concentrate receipts; terrestrial concentrate terms, not an offtake
  contract for meteorite phases, and no value uses them (General_Research
  rc-849).

## Facts the comments state

Cited in code comments beside a value they explain; none reaches a value.

- **NASA NSSDCA, *Mars Fact Sheet***,
  <https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html>: the CO2 and
  N2 fractions and surface pressure behind `mars_surface`'s utility comments in
  `spacevalue/catalog.py` (General_Research rc-165).
- **Comparators beside `IN_SPACE_UTILITY`, every factor an engineering
  scenario** (rc-424 to rc-483). Each is scoped to the claim its comment
  makes; none establishes a utility fraction, a throughput, a demand or a
  cost. Full references since 0.7.2 (General_Research rc-787, rc-796, rc-800
  to rc-803):
  - Structural metals: **Roberts, Ledbetter, Jones, Courtright & Blanchard
    2023**, *NASA Technology Maturation Plan for In-space Manufacturing of
    Metals*, 34th Annual Solid Freeform Fabrication Symposium, NTRS
    20230012701, <https://ntrs.nasa.gov/citations/20230012701>; and
    **Mulvaney, Arney et al. 2026**, *In-Space Servicing, Assembly, and
    Manufacturing (ISAM) State of Play 2026 Edition*, NASA Langley, NTRS
    20260008638, <https://ntrs.nasa.gov/citations/20260008638>, p. 266
    (PGM07, ESA's MELT first-metal-printer ISS demonstration and its
    four-print comparison). Manufacturing maturity only.
  - Silicates as shielding: **Kim, Wilson, Thibeault, Nealy, Badavi & Kiefer
    1994**, *Performance Study of Galactic Cosmic Ray Shield Materials*, NASA
    TP-3473, NTRS 19950010497, <https://ntrs.nasa.gov/citations/19950010497>,
    Fig. 15: the relative GCR cell-transformation metric of water and dry
    regolith at 10–30 g/cm². Shielding context; the 0.25 factor also carries
    feedstock and market judgement.
  - Organics: **Lewis, J. S. 1992**, *Asteroid resources*, in *Space
    Resources, Volume 3: Materials*, NASA SP-509, pp. 59–78, NTRS
    19930007691, <https://ntrs.nasa.gov/citations/19930007691>, PDF p. 6
    (up to 6% organic matter: an asteroid inventory, not a demand); and
    **Morren, Hay, Haag & Sovey 1987**, *Preliminary performance
    characterizations of an engineering model multipropellant resistojet for
    space station application*, NASA TM-100113 / AIAA 87-2120, NTRS
    19870014388, <https://ntrs.nasa.gov/citations/19870014388>, PDF p. 2
    (methane among the station's resistojet fluids; also the CO2 entry).
  - Ammonia and nitrogen: **Deininger, Chopra, Pivirotto, Goodfellow &
    Barnett 1990**, *The 30-kW Ammonia Arcjet Technology Final Report*, JPL
    Publication 90-4, NTRS 19900015874,
    <https://ntrs.nasa.gov/citations/19900015874>, p. 41 (below 800 s);
    **Hardy & Curran 1987**, *Low Power dc Arcjet Operation With
    Hydrogen/Nitrogen/Ammonia Mixtures*, NASA TM-89876 / AIAA 87-1948, NTRS
    19870013371, <https://ntrs.nasa.gov/citations/19870013371>, pp. 9 and 25;
    and **Masangkay, Sweterlitsch & Frahlman 2026**, *Supplying Nitrogen on
    Future Missions to the Moon and Mars*, ICES-2026-238, NTRS 20260003060,
    <https://ntrs.nasa.gov/citations/20260003060>, Table 4 (9–4,620 kg of
    nitrogen a mission, by destination).
  - CO2 and carbon: **Franco, Devor, Snyder, Petersen & Hintze 2019**,
    *Study of Sabatier Catalyst Performance for a Mars ISRU Propellant
    Production Plant*, ICES-2019-077, NTRS 20190027280,
    <https://ntrs.nasa.gov/citations/20190027280>, p. 2 (the Sabatier feed;
    not where its CO2 comes from); **Moses & Bushnell 2016**, *Frontier
    In-Situ Resource Utilization for Enabling Sustained Human Presence on
    Mars*, NASA/TM-2016-219182, NTRS 20160005963,
    <https://ntrs.nasa.gov/citations/20160005963>, sec. 3.1.2, printed p. 6
    (Mars plastics from CO2 and H2, not asteroid carbon); and **Lewis 2016**,
    *In-Space Production of Storable Propellants*, NIAC Phase I Final Report
    for NNX15AL85G, NTRS 20190001542,
    <https://ntrs.nasa.gov/citations/20190001542>, pp. 30 and 33 (352 t of CO2
    per 1,000 t of propellant; it does not take the CO2 from carbonates).
  - Phosphorus: **Wade 1989**, *Nutritional models for a Controlled
    Ecological Life Support System (CELSS): Linear mathematical modeling*,
    NASA CR-4229, NTRS 19890011244,
    <https://ntrs.nasa.gov/citations/19890011244>, p. 60; and **Zeitlin,
    Wheeler & Lunn 2015**, *Plant Biomass Leaching for Nutrient Recovery in
    Closed Loop Systems Project*, KSC Center Innovation Fund, NTRS
    20160006646, <https://ntrs.nasa.gov/citations/20160006646>, pp. 3 and 5
    (a 60% recovery target, not an achieved fraction).
  - Sulfur: **Abney, Nalette, Knox et al. 2026**, *An Evaluation of
    Technology to Mitigate Freon R-218, Carbon Disulfide, and Carbonyl
    Sulfide Contamination to Support Sabatier Integrated Operations*,
    ICES-2026-601, NTRS 20260003516,
    <https://ntrs.nasa.gov/citations/20260003516>, PDF p. 2 ("sulfur and
    silicon were the most detrimental poisons" of ISS's flight catalyst); and
    **Grugel 2008**, *Sulfur "Concrete" for Lunar Applications—Environmental
    Considerations*, NASA/TM-2008-215250, NTRS 20080022947,
    <https://ntrs.nasa.gov/citations/20080022947>, pp. 1–2 and 33 (concrete
    from recovered lunar troilite sulfur: a post-extraction comparator, not
    raw sulfide utility).
- **Beside the world-production ceilings and the water price**, none a new
  value (General_Research rc-523, rc-524, rc-527, rc-529, rc-602): USGS,
  *Mineral Commodity Summaries 2026*, Silver (26,000 t mined, 2025e) and
  Sulfur (83.9 Mt for 2024, 84.0 Mt 2025e, p. 2) chapters; Johnson Matthey,
  *PGM Market Report 2026*, pp. 32-34 (2025 primary supply of iridium,
  rhodium and ruthenium, a different series from the scenario figures);
  Matos et al. 2021, JRC EUR 30704 EN, sec. 7.2, p. 31 (world elemental P4
  900-1,200 kt/yr, precise figure unknown); and Metropolitan Utilities
  District (Omaha), *Schedule W-3*, effective 2 Jan 2026 (an industrial
  water tariff beside the earth-surface water scenario).
- **Beside the demand shares and prices**: Kornuta et al. 2019 and LunA-10
  (rc-432); USGS MCS 2025 amorphous graphite and Platts N330 carbon black
  (rc-508); Cabri, Harris & Weiser 1996 (native PGM, rc-512); Kutyrev et
  al. 2023, Lithosphere 2023(1):126 (awaruite, rc-513); IMF WP 2024/077 and
  Banque de France Eco Notepad 419 (elasticity, rc-507).

## Delivery-route figures in the destination notes

The `notes` column's route sentences interpolate spacecost's delivery
chains; these are the studies the sentences name (General_Research rc-769
to rc-771). The delta-v rows themselves are spacecost's, cited there.

- **NASA, *Human Exploration of Mars Design Reference Architecture 5.0***,
  NASA/SP-2009-566 (2009), printed p. 22: the 250 x 33,793 km 1-sol staging
  orbit. The 2,100 m/s 200-km comparator beside it is a two-body calculation
  (spacecost's low-Mars-orbit TEI row), not a DRA figure.
- **Edquist et al. 2022**, Table 3 (PDF p. 14): the entry masses behind the 28.5% (MSL) and 30.5% (Perseverance)
  entry-to-rover ratios, with the rover masses from JPL's MSL fact sheet and
  NASA's Mars 2020 flight-mechanics paper (spacecost `delivery.py`).
- **NASA-CR-195527**, Table 2.1 (3,140 m/s TLI from a 185 km orbit), and
  **Benson, Asher & Reese 2025**, NTRS 20250000718, slide 5 (400-450 m/s TLI
  to NRHO): the two halves of the cislunar sum, from different missions.
- **NASA SP-4029**, *Apollo by the Numbers*: the TLI, lunar-orbit insertion
  and LM powered-descent figures of the lunar-surface route.

## Software

- **spacecost** (MIT, the same author): the delivery chains, the launch price
  and the quote-snapshot code. Pinned to a tagged release in `pyproject.toml`.
- **numpy** and **pandas** (BSD-3-Clause). **yfinance** (Apache-2.0) and
  **requests** (Apache-2.0) only for live quotes.

## Citing this package

Cite the release you used, by its tag (`prices-YYYY-MM-DD` for the tables,
`vX.Y.Z` for the code), and the data contract stamped in its rows.
