# -*- coding: utf-8 -*-
"""What a hold of asteroid ore is worth, and how much of it a market takes.

The phase walk (minerals, their element yields, the phases no process
separates), the flown refinery, the composition memo, the market ceilings and
the payload knapsack that chooses what a mission carries home.

This is economicspace's cargo valuation.  It was Stage 4 (`modules/calc.py`,
calc 1.32.0) until spacevalue 0.2.0, and it moved VERBATIM: every line below
the imports is calc's, comments included, so "this module", "Module 1/3" and
version numbers such as v1.21.0 are calc's words and calc's stamps (economicspace
`versions.md`, "Stage 4 changelog").  economicspace imports these names and
flies the payload they choose.

Rules that follow from that:

- **A change here that moves one float moves economicspace's numbers.**  That
  repository argues every release from bit-identical output, so such a change
  is a calc release there, and `tests/test_cargo_golden.py` replays recorded
  calls from a real run and fails on the last bit.  Re-associating an
  expression is such a change.
- **Pure.**  No config, no I/O, no printing, and importing this module imports
  neither the price catalog nor spacecost: a Stage 4 worker imports it at
  spawn.  The caches are module globals, each keyed on an argument's
  identity or on a value; see each one.
- **Private names are a contract.**  calc reads several of them
  (`tests/test_consumer_contract.py`, CARGO_SURFACE).
"""
import functools
import json
from typing import (Any, Dict, Iterator, List, Mapping, Optional, Tuple,
                    Union)

import pandas as pd

# A row of one of the upstream catalogs, as calc defines it: everything that
# reads one uses only `.get(key)` and `[key]`, which a dict and a Series serve
# identically.
Row = Mapping[str, Any]


# ─────────────────────────────────────────────────────────────────────────────
# MINERAL-VALUE LOOKUPS
# ─────────────────────────────────────────────────────────────────────────────
# Rare-metal elements that get scaled by per-asteroid PGM-enrichment
# factor (Module 1 v1.0.4's comp_pgm_enrichment column).  The base metals
# (iron, nickel, cobalt) in nickel-iron alloy are NOT scaled; they are
# bulk Fe-Ni alloy abundance, not PGM enrichment.
RARE_METAL_ELEMENTS: set = {
    "platinum", "palladium", "rhodium",
    "iridium",  "osmium",    "ruthenium",
    "gold",
}


# Same single-slot memo as _OPS_CACHE, for the mineral table.  Every asteroid
# re-prices the same 4 bulk minerals, and nickel-iron alone fans out to ~10
# element lookups, so this is ~19 full-DataFrame scans per asteroid otherwise.
# Holds price and yields side by side since both are keyed by mineral name.
_MINERAL_CACHE: Tuple[Optional[pd.DataFrame], Dict[str, Tuple[Optional[float], str]]] = (None, {})


def _mineral_table(mineral_df: pd.DataFrame) -> Dict[str, Tuple[Any, ...]]:
    """name → (price, yields_json, net price, refining kWh/kg, used in space).

    Built once and memoised.  The last three are v1.25.0's and are read only
    when the refinery flies; see `load_all_catalogs`.
    """
    global _MINERAL_CACHE
    cached_df, mapping = _MINERAL_CACHE
    if cached_df is mineral_df:
        return mapping

    has_yields = "yields_json" in mineral_df.columns
    yields_col = mineral_df["yields_json"] if has_yields else [None] * len(mineral_df)
    # v1.25.0: three more fields, read only when the refinery flies (see
    # `load_all_catalogs`); a table without them fills them with None, 0.0
    # and False, and the first two fields are exactly what they always were.
    n = len(mineral_df)
    net_col = (mineral_df[_NET_PRICE_COL] if _NET_PRICE_COL in mineral_df.columns
               else [None] * n)
    kwh_col = (mineral_df["refining_kwh_per_kg"]
               if "refining_kwh_per_kg" in mineral_df.columns else [0.0] * n)
    route_col = (mineral_df["value_route"] if "value_route" in mineral_df.columns
                 else [None] * n)

    mapping = {}
    for name, price, yields, net, kwh, route in zip(
        mineral_df["name"], mineral_df["price_usd_per_kg"], yields_col,
        net_col, kwh_col, route_col,
    ):
        key = str(name)
        if key in mapping:
            continue                      # first match wins, as .iloc[0] did
        mapping[key] = (
            float(price) if pd.notna(price) else None,
            yields if isinstance(yields, str) else "",
            float(net) if net is not None and pd.notna(net) else None,
            float(kwh) if kwh is not None and pd.notna(kwh) else 0.0,
            route == "used in space",
        )
    _MINERAL_CACHE = (mineral_df, mapping)
    return mapping


_MARKET_CACHE: Tuple[Optional[pd.DataFrame], Dict[str, float]] = (None, {})


def market_table(mineral_df: pd.DataFrame) -> Optional[Dict[str, float]]:
    """name → annual absorbable quantity (kg/yr), memoised.

    Returns None for a pre-v1.5.0 Module 2 catalog that carries no
    `annual_market_kg` column, which switches saturation modelling off rather
    than silently assuming an infinite market.
    """
    global _MARKET_CACHE
    cached_df, mapping = _MARKET_CACHE
    if cached_df is mineral_df:
        return mapping or None
    if "annual_market_kg" not in mineral_df.columns:
        _MARKET_CACHE = (mineral_df, {})
        return None
    mapping = {}
    for name, qty in zip(mineral_df["name"], mineral_df["annual_market_kg"]):
        if pd.notna(qty):
            mapping.setdefault(str(name), float(qty))
    _MARKET_CACHE = (mineral_df, mapping)
    return mapping or None


def _mineral_price(mineral_df: pd.DataFrame, name: str) -> Optional[float]:
    """Look up `price_usd_per_kg` for a mineral / element by exact name."""
    entry = _mineral_table(mineral_df).get(name)
    return None if entry is None else entry[0]


def _mineral_implied_value(
    mineral_df:     pd.DataFrame,
    mineral_name:   str,
    pgm_enrichment: float = 1.0,
) -> Optional[float]:
    """For a mineral, compute its bulk $/kg from elemental yields.

    Mirrors Module 2's `mineral_to_element_value` but scales the rare-metal
    portion (Pt, Pd, Rh, Ir, Os, Ru, Au) by `pgm_enrichment`, the per-
    asteroid factor sourced from Module 1's comp_pgm_enrichment column.
    Base metals (Fe, Ni, Co) and non-PGM yields are unaffected.

    For pgm_enrichment = 1.0 the behaviour is identical to the v1.3.3
    function (chondritic / mean-iron-meteorite baseline).  For an M-type
    asteroid with comp_pgm_enrichment = 2.0, the PGM portion doubles.

    Returns the direct row price as a fallback if yields are empty.
    """
    entry = _mineral_table(mineral_df).get(mineral_name)
    if entry is None:
        return None

    try:
        yields = json.loads(entry[1] or "{}")
    except (json.JSONDecodeError, TypeError, AttributeError):
        yields = {}

    if not yields:
        return _mineral_price(mineral_df, mineral_name)

    enrichment = float(pgm_enrichment) if pgm_enrichment else 1.0
    total = 0.0
    for element, fraction in yields.items():
        elem_price = _mineral_price(mineral_df, element)
        if elem_price is None:
            continue
        eff_fraction = float(fraction)
        if element in RARE_METAL_ELEMENTS:
            eff_fraction *= enrichment
        total += eff_fraction * elem_price
    return total if total > 0 else _mineral_price(mineral_df, mineral_name)


# ─────────────────────────────────────────────────────────────────────────────
# PER-ASTEROID BULK-MATERIAL $/kg
# ─────────────────────────────────────────────────────────────────────────────
# The asteroid's composition is assumed uniform (per user spec).  Mined
# bulk material is therefore a weighted blend of:
#   metal_fraction      × nickel-iron implied value  (Fe + Ni + Co + PGMs)
#   silicate_fraction   × silicates bulk price       ($0.05/kg-class)
#   carbon_fraction     × carbon bulk price          ($0.20/kg-class)
#   ice_fraction        × water price                ($2,500/kg in-space proxy)
#
# This maps Module 1's broad taxonomy fractions onto the most-appropriate
# Module 2 row.  An X-complex (M-type) asteroid is dominated by metal_frac;
# a C-complex by carbon + silicate + ice; a V-type by silicate.

FRACTION_TO_MINERAL: Dict[str, str] = {
    "comp_metal_fraction":    "nickel-iron",
    "comp_silicate_fraction": "silicates",
    "comp_carbon_fraction":   "carbon",
    "comp_ice_fraction":      "water",
}


# ─── MINERAL PHASES  (v1.24.0) ───────────────────────────────────────────────
# Module 1 (catalog data contract 1.7.0) divides each body into the minerals
# its four coarse fractions are made of: `comp_phases`, a JSON object of mass
# fractions by phase name, spelled as Stage 2 spells its rows.  When a row
# carries it, the three valuation functions below walk the PHASES instead of
# FRACTION_TO_MINERAL.  The phases of each coarse group add back to that group's
# fraction (AsteroidCatalog's tests hold it), and the accessory phases --
# troilite, magnetite, chromite, ilmenite, spinel, carbonates -- are carved out
# of the residual, so the "other (bulk silicate)" floor gets smaller.
_PHASES_COL = "comp_phases"

# v1.26.0: the same, one level down (catalog data contract 1.8.0): the alloy
# as kamacite / taenite / tetrataenite / cohenite, the sulfide by species,
# and the phosphates and CAI oxides named.  `load_all_catalogs` keeps at most
# one of the two columns, so a row carries the one the run chose.
_DETAILED_COL = "comp_phases_detailed"


def _row_phases_text(asteroid_row: Row) -> Any:
    """The row's phase JSON, from whichever phase column it carries.

    The detailed column when the row has it, which after `load_all_catalogs`
    means the run chose it; a hand-built row carrying both is read as the
    detailed model, and one that wants the other drops the column first.
    """
    if _DETAILED_COL in asteroid_row:
        return asteroid_row.get(_DETAILED_COL)
    return asteroid_row.get(_PHASES_COL)


# ⚠️  `maxsize=None` IS SAFE HERE AND NAMED AS SUCH: the key is the JSON
# string, one per taxonomy row Module 1 reads (a few dozen), whatever the size
# of the catalog.  That is the rule "Where a cache is safe" gives: unbounded
# exactly when you can name the ceiling.
@functools.lru_cache(maxsize=None)
def _parse_phases(text: str) -> Tuple[Tuple[str, float], ...]:
    """(phase, fraction) pairs from one `comp_phases` cell, zeros dropped.

    A tuple, so the cached value cannot be mutated by a caller.  Order is the
    catalog's, which is fixed per class (group, then table order).
    """
    return tuple((str(name), float(frac))
                 for name, frac in json.loads(text).items() if float(frac) > 0.0)


def _row_phases(asteroid_row: Row) -> Optional[Tuple[Tuple[str, float], ...]]:
    """The row's phases, or None when it has none (older catalog, switch off,
    or an Unknown-class body, whose cell is empty)."""
    text = _row_phases_text(asteroid_row)
    if isinstance(text, str) and text:
        return _parse_phases(text)
    return None


# ─── WHAT A BENEFICIATION STEP CANNOT SEPARATE  (v1.26.0) ────────────────────
# The detailed phases name the three Fe-Ni alloys, and they are not three
# products.  Kamacite and taenite are intergrown in the same metal grains -- the
# Widmanstatten plates and the plessite between them -- and tetrataenite is a
# rim on the taenite, so no physical separation takes one without the others:
# the metal leaves the rock as ONE concentrate, in the proportions the class
# holds.  So they are sold as one product, keyed `nickel-iron` (the row whose
# market and demand class they share), at the fraction-weighted blend of their
# values, which is where the class-specific nickel and platinum show.
#
# 🚨  FOUND BY MEASURING, NOT BY THINKING.  The first build loaded them as three
# phases, and the concentration search bounds itself on the fraction of the
# SINGLE best phase (`saturation_ratio`): tetrataenite is fractionally the
# richest alloy, so an S-type's best phase fell from 6% of the body to 0.4%,
# the search range widened fourteen-fold, and the beneficiated cells moved in
# both directions by up to 43% for no physical reason.  The knapsack would also
# have loaded pure taenite ahead of kamacite whenever the hold was the limit,
# a grade no process can make.
#
# Cohenite and schreibersite stay separate phases: they are discrete crystals,
# as schreibersite has been since v1.24.0.  A phase not named here is its own
# product, and takes exactly the path it took before.
_INSEPARABLE: Dict[str, str] = {
    "kamacite":     "nickel-iron",
    "taenite":      "nickel-iron",
    "tetrataenite": "nickel-iron",
}


@functools.lru_cache(maxsize=None)
def _phase_products(
    phases: Tuple[Tuple[str, float], ...],
) -> Tuple[Tuple[str, Tuple[Tuple[str, float], ...]], ...]:
    """(product, its member phases) in first-appearance order.

    A product of one member is that phase unchanged.  Keyed on the parsed
    phase tuple, of which there are a few dozen, so the unbounded cache has a
    ceiling it can name.
    """
    order: List[str] = []
    members: Dict[str, List[Tuple[str, float]]] = {}
    for name, frac in phases:
        product = _INSEPARABLE.get(name, name)
        if product not in members:
            order.append(product)
            members[product] = []
        members[product].append((name, frac))
    return tuple((product, tuple(members[product])) for product in order)


def _blend(members: Tuple[Tuple[str, float], ...], value) -> Optional[Tuple[float, float]]:
    """(fraction, fraction-weighted mean of `value`) over the members it prices.

    A member `value` returns None for is left out, as an unpriced phase is
    left out of the walk; None when none is priced.
    """
    frac = total = 0.0
    for name, f in members:
        v = value(name)
        if v is None:
            continue
        frac += f
        total += f * float(v)
    if frac <= 0.0:
        return None
    return frac, total / frac


def _row_water_fraction(asteroid_row: Row) -> float:
    """Mass fraction of the body that is WATER, which is not always all its ice.

    v1.24.0.  Three readers took `comp_ice_fraction` as water: ISRU feed, the
    per-body context, and the cargo-water bake.  For a hydrated C-type that is
    right, its "ice" is bound water.  For D, Z, P and T the phases split the
    ice into water, CO2 and ammonia, and reading all of it as water would make
    propellant out of carbon dioxide.  Without phases, the old reading stands.
    """
    phases = _row_phases(asteroid_row)
    if phases is not None:
        for name, frac in phases:
            if name == "water":
                return frac
        return 0.0
    ice = asteroid_row.get("comp_ice_fraction")
    if ice is None or pd.isna(ice):
        return 0.0
    return float(ice)


def _phase_value(
    mineral_df: pd.DataFrame, phase: str, pgm_enrichment: float,
) -> Optional[float]:
    """$/kg of one phase: the better of selling it AS IT IS, or REFINED.

    v1.24.0.  A mineral row in Stage 2 has two prices and until now Stage 4
    read one.  Its own `price_usd_per_kg` is the mineral used for itself --
    olivine as shielding rock, troilite as a sulfide.  Its yields are what it
    is worth taken apart -- olivine's 10% iron, troilite's iron and sulfur.
    `_mineral_implied_value` returns the yields whenever there are any, so
    olivine was worth its iron and nothing for the 90% that is rock: fine while
    nothing read olivine, and wrong the moment the phases do.  A buyer does the
    better of the two, so the value is the larger.  Enrichment scales only the
    rare-metal yields, in whichever phase carries them.

    Only the phase walk uses this.  The four-fraction walk keeps
    `_mineral_implied_value`, so switching phases off is the old model exactly.
    """
    if refinery_flown(mineral_df):
        return _phase_terms(mineral_df, phase, pgm_enrichment, True)[0]
    refined = _mineral_implied_value(mineral_df, phase, pgm_enrichment)
    as_is = _mineral_price(mineral_df, phase)
    values = [v for v in (refined, as_is) if v is not None]
    return max(values) if values else None


# ─── THE REFINERY, FLOWN  (v1.25.0) ──────────────────────────────────────────
# Stage 2 writes, per commodity, the energy to turn a kilogram of its raw
# feedstock into a usable product (`refining_kwh_per_kg`) and its price before
# the dollar deduction that energy and an amortised plant used to take out of
# it (`price_before_processing_usd_per_kg`).  With `model_refinery` on, Stage 4
# values the hold at the second and flies the first: energy through the array,
# plant through the rig.  See `CalcConfig.model_refinery`.
_REFINING_COLS = ("refining_kwh_per_kg", "price_before_processing_usd_per_kg",
                  "value_route")
_NET_PRICE_COL = "price_net_usd_per_kg"


def refinery_flown(mineral_df: pd.DataFrame) -> bool:
    """True when `load_all_catalogs` switched this table to gross prices."""
    return _NET_PRICE_COL in mineral_df.columns


def _yield_terms(
    mineral_df: pd.DataFrame, phase: str, pgm_enrichment: float,
) -> Tuple[Optional[float], Optional[float], float]:
    """(gross, net, Wh/kg) of one mineral TAKEN APART into its yields.

    The same walk as `_mineral_implied_value`, over both price columns at
    once.  Energy is the mineral's own breakdown energy plus each element's,
    and only for what is refined HERE: an element shipped home is refined on
    Earth, inside its terrestrial price, and a mineral none of whose elements
    is used in space is taken apart on Earth too.  (None, None, 0.0) for a
    mineral with no yields.
    """
    table = _mineral_table(mineral_df)
    entry = table.get(phase)
    if entry is None:
        return None, None, 0.0
    try:
        yields = json.loads(entry[1] or "{}")
    except (json.JSONDecodeError, TypeError, AttributeError):
        yields = {}
    if not yields:
        return None, None, 0.0
    enrichment = float(pgm_enrichment) if pgm_enrichment else 1.0
    gross = net = 0.0
    element_wh = 0.0
    any_here = False
    for element, fraction in yields.items():
        e = table.get(element)
        if e is None or e[0] is None:
            continue
        share = float(fraction)
        if element in RARE_METAL_ELEMENTS:
            share *= enrichment
        gross += share * e[0]
        net += share * (e[2] if e[2] is not None else e[0])
        if e[4]:
            any_here = True
            element_wh += float(fraction) * e[3] * 1000.0
    if gross <= 0:
        return None, None, 0.0
    wh = (entry[3] * 1000.0 if any_here else 0.0) + element_wh
    return gross, net, wh


def _phase_terms(
    mineral_df: pd.DataFrame, phase: str, pgm_enrichment: float, phased: bool,
) -> Tuple[Optional[float], float]:
    """($/kg, refining Wh/kg) of one phase, by the route it is sold by.

    Only meaningful when the refinery flies (`refinery_flown`): the price is
    then the GROSS one, and the energy is what the flown refinery spends per
    kilogram of this phase in the hold.  Not memoised itself: both callers
    are, per composition.
    """
    entry = _mineral_table(mineral_df).get(phase)
    if entry is None:
        return None, 0.0
    as_is_gross, as_is_net = entry[0], entry[2]
    as_is_wh = entry[3] * 1000.0 if entry[4] else 0.0
    gross, net, wh = _yield_terms(mineral_df, phase, pgm_enrichment)
    if gross is None:
        return as_is_gross, (as_is_wh if as_is_gross is not None else 0.0)
    if not phased:
        # The four-fraction walk's only rule: a mineral with yields is priced
        # by them.  Unchanged by the refinery; only who pays moves.
        return gross, wh
    # The route is decided on NET prices, which is Stage 2's own estimate of
    # what each costs to deliver usable; the refinery then charges the flown
    # cost of the route chosen.  A tie is sold as it is.
    if as_is_net is None or net > as_is_net:
        return gross, wh
    return as_is_gross, as_is_wh


def asteroid_refinery(
    asteroid_row: Row, mineral_df: pd.DataFrame,
) -> Optional[Tuple[Dict[str, float], float]]:
    """({phase: refining Wh per kg in the hold}, Wh per kg of run-of-mine ore).

    None when the refinery does not fly.  The phases are exactly
    `asteroid_phase_table`'s, the residual included (sold as silicates, so it
    takes silicates' energy), and the second figure is their fraction-weighted
    sum, which is what a raw hold of the body's own proportions spends.
    """
    if not refinery_flown(mineral_df):
        return None
    # Memoised per composition, like the three functions above it: it runs
    # once per catalog row and has a couple of dozen distinct answers.
    key = _composition_key(asteroid_row)
    if key is not None:
        entries = _composition_cache(mineral_df)
        hit = entries.get(key)
        if hit is not None and hit.refinery is not None:
            return hit.refinery
    pgm = _pgm_enrichment(asteroid_row)
    phases = _row_phases(asteroid_row)
    phased = phases is not None
    # v1.26.0: a product of several phases spends their blended energy, by
    # the same weights its price is blended by.
    merged = ({product: members for product, members in _phase_products(phases)
               if len(members) > 1} if phased else {})
    wh: Dict[str, float] = {}
    raw = 0.0
    for name, frac, _price in asteroid_phase_table(asteroid_row, mineral_df):
        key = "silicates" if name == _RESIDUAL_PHASE else name
        if name in merged:
            terms = {n: _phase_terms(mineral_df, n, pgm, True) for n, _f in merged[name]}
            blended = _blend(merged[name], lambda n: (
                terms[n][1] if terms[n][0] is not None else None))
            per_kg = blended[1] if blended is not None else 0.0
            wh[name] = per_kg
            raw += frac * per_kg
            continue
        per_kg = _phase_terms(mineral_df, key, pgm,
                              phased and name != _RESIDUAL_PHASE)[1]
        wh[name] = per_kg
        raw += frac * per_kg
    result = (wh, raw)
    if key is not None:
        _composition_entry(entries, key).refinery = result
    return result


def refinery_plant_kg(hold_kg: float, stay_yr: float, kg_per_yr_per_kg: float) -> float:
    """Mass of the plant that processes `hold_kg` in `stay_yr` (v1.25.0).

    Module 3's "In-space processing plant throughput" is kilograms processed
    per year per kilogram of plant, so the plant is the hold's rate over it.
    """
    if hold_kg <= 0 or stay_yr <= 0 or kg_per_yr_per_kg <= 0:
        return 0.0
    return hold_kg / (stay_yr * kg_per_yr_per_kg)


def _hold_refining(
    refinery: Optional[Tuple[Dict[str, float], float]],
    phases:   Optional[list],
    payload_kg: float,
    feed_kg:  float,
    beneficiate: bool,
    recovery: float,
) -> Tuple[float, Optional[float]]:
    """(refining Wh for this hold, water kg in it or None if not computed).

    A raw hold is the body's proportions, so its energy is the per-kg figure
    times the payload.  A concentrated hold is whatever the knapsack loads,
    so the knapsack is asked ONCE for its whole mix, and the water in it is
    returned too, so the caller does not ask it a second time for that.
    """
    if refinery is None or payload_kg <= 0:
        return 0.0, None
    per_phase, raw_wh_per_kg = refinery
    if not beneficiate or not phases:
        return payload_kg * raw_wh_per_kg, None
    mix = optimal_payload_mix(payload_kg, feed_kg, phases, recovery)["mix_kg"]
    wh = 0.0
    for name, kg in mix.items():
        wh += kg * per_phase.get(name, 0.0)
    return wh, float(mix.get("water", 0.0))


# ── Composition is a per-TAXONOMY fact, not a per-row one  (v1.17.6) ────────
# `asteroid_bulk_value_usd_per_kg`, `asteroid_phase_table` and
# `asteroid_best_phase_usd_per_kg` read exactly five values off the row, the
# PGM enrichment and the four taxonomy fractions, and nothing else.  All five
# come out of the catalog builder's `enrich_composition`: 76 distinct types
# across 1,555,667 rows, collapsing to ~25 distinct composition tuples (11 in a
# 4,000-row stride).
#
# ⚠️  KEYED ON THE FIVE VALUES, NOT ON `spectral_type`, AND SINCE CATALOG DATA
# CONTRACT 1.4.0 THAT IS LOAD-BEARING.  The builder now gives every body past
# 5.5 AU a D-type composition whatever class a source reported, so the tuple is
# no longer a function of the type column alone (30 rows in `data-2026-09-25`).
# A memo keyed on the type would price those bodies as the rock their colour
# class names.
#
# So `evaluate_asteroid` was walking `FRACTION_TO_MINERAL` three times per
# asteroid, with a `pd.isna` on a scalar per entry, at ~1 us each, to
# re-derive one of a couple of dozen answers, once for every body in the
# catalog.  Measured on a 4,000-row stride of the real catalog:
#
#     asteroid_bulk_value_usd_per_kg   14.84 us/row  ->  23.1 s / full pass
#     asteroid_phase_table             13.97 us/row  ->  21.7 s / full pass
#     asteroid_best_phase_usd_per_kg   27.66 us/row  ->  43.0 s / full pass
#
# ~88 s of every full-catalog pass, paid by every row whether or not it turns
# out to be evaluable.  Exactly the pattern v1.17.4 found on both sides of the
# CSV boundary, "a column with few distinct values and one Python call per
# row", in the one place between them that release did not look.
#
# ⚠️  `asteroid_best_phase_usd_per_kg` calls the bulk function itself, so a
# beneficiated run computed the bulk value TWICE per asteroid.  The memo closes
# that as a side effect; it is not a separate change.
#
# Bit-identical by construction: the same key re-runs the same walk over the
# same mineral table, so the cached floats ARE the floats the walk produced.
_COMPOSITION_CACHE: Tuple[Any, Dict[Tuple[Any, ...], Any]] = (None, {})


def _composition_cache(mineral_df: pd.DataFrame) -> Dict[Tuple[Any, ...], Any]:
    """The memo for `mineral_df`, cleared when the frame changes.

    Single-slot on frame IDENTITY, the same shape as `_MINERAL_CACHE`,
    `_MARKET_CACHE` and `_OPS_CACHE`, prices are what the answers are made of,
    so a re-priced Stage 2 catalog must not read a cached value.
    """
    global _COMPOSITION_CACHE
    cached_df, entries = _COMPOSITION_CACHE
    if cached_df is not mineral_df:
        entries = {}
        _COMPOSITION_CACHE = (mineral_df, entries)
    return entries


# The five values the three functions below read, in a fixed order.
_COMPOSITION_KEY_COLS: Tuple[str, ...] = (
    ("comp_pgm_enrichment",) + tuple(FRACTION_TO_MINERAL)
)


class _CompositionValues:
    """The three composition-derived answers, filled in as they are asked for.

    A tiny `__slots__` object rather than a mutable 3-list because the three
    fields are read by name in three different functions and a positional index
    would be one more thing to keep in step -- the same reason
    `_ops_cost_constants` is unpacked in a single statement.  `None` means "not
    computed yet", which is distinguishable from every value these three can
    legitimately return (all are floats, or a list).
    """
    __slots__ = ("bulk", "phases", "best", "refinery")

    def __init__(self) -> None:
        """All three slots start as None, meaning "not computed yet".

        Distinguishable from every value they can legitimately hold, which are
        all floats or a list, so a miss is never confused with a real answer of
        zero. `__slots__` is what keeps ~25 of these off the per-instance dict.
        """
        self.bulk = None
        self.phases = None
        self.best = None
        self.refinery = None      # v1.25.0, `asteroid_refinery`


def _composition_entry(
    entries: Dict[Tuple[Any, ...], "_CompositionValues"], key: Tuple[Any, ...],
) -> "_CompositionValues":
    """The entry for `key`, created empty on first use."""
    hit = entries.get(key)
    if hit is None:
        hit = entries[key] = _CompositionValues()
    return hit


def _composition_key(asteroid_row: Row) -> Optional[Tuple[Any, ...]]:
    """Hashable identity of a row's composition, or None if it is not cacheable.

    ⚠️  NaN and None normalise to the SAME key, and that is required rather
    than convenient: all three consumers test `x is None or pd.isna(x)` and
    take the identical branch either way, so two rows that differ only in how
    their missing value is spelled must share an answer.  A bare `float('nan')`
    key would also never hit, two NaNs are not equal, so the cache would
    silently stop caching for exactly the rows that have gaps, which is the
    quiet-wrong-answer shape in its performance clothing (see `_UNSET` in
    `_isru_propellant_consts`).

    ⚠️  Anything that is not a real number or None returns None, which sends
    the caller down the uncached path rather than inventing a key for a value
    whose branch behaviour has not been checked.  `to_dict("records")` on the
    float64 composition columns yields plain floats, so the fast path is what
    the pipeline actually takes; this is the door for a hand-built row.
    """
    key: List[Any] = []
    for col in _COMPOSITION_KEY_COLS:
        v = asteroid_row.get(col)
        if v is None:
            key.append(None)
        elif isinstance(v, float):
            key.append(None if v != v else v)          # NaN -> None
        elif isinstance(v, int) and not isinstance(v, bool):
            key.append(float(v))
        else:
            return None
    # v1.24.0: the phases decide the answer too, so they are part of the key.
    # The JSON string itself: a few dozen distinct values, and two rows share
    # an answer exactly when they share it.  None when absent, so a row
    # without phases keys exactly as before.
    text = _row_phases_text(asteroid_row)
    key.append(text if isinstance(text, str) and text else None)
    return tuple(key)


def _pgm_enrichment(asteroid_row: Row) -> float:
    """Per-asteroid PGM enrichment, defaulted to the chondritic baseline.

    Module 1 has supplied `comp_pgm_enrichment` since v1.0.4; 1.0 is what an
    older catalog means, not a missing value to reject.
    """
    pgm = asteroid_row.get("comp_pgm_enrichment")
    if pgm is None or pd.isna(pgm):
        return 1.0
    return float(pgm)


def _phase_prices(
    asteroid_row: Row, mineral_df: pd.DataFrame,
) -> Iterator[Tuple[str, float, float]]:
    """(phase, fraction, usd_per_kg) for every phase actually PRESENT.

    The one walk of `FRACTION_TO_MINERAL` shared by `asteroid_phase_table` and
    `asteroid_best_phase_usd_per_kg`, which had it written out twice.  Phases
    with no fraction or no price are skipped; you cannot select what is not
    there.

    ⚠️  `asteroid_bulk_value_usd_per_kg` deliberately does NOT use this: it
    admits a fraction of exactly 0.0 where this skips it.  Unifying the third
    copy would be numerically negligible and would still cost the bit-identity
    every release here is argued from; see the v1.14.2 phase-sort warning.
    """
    pgm_enrichment = _pgm_enrichment(asteroid_row)
    phases = _row_phases(asteroid_row)
    if phases is not None:
        # v1.24.0: the minerals, each at the better of as-is and refined.
        # v1.26.0: the ones no process separates, as the one product they
        # are; see `_INSEPARABLE`.  A lone phase takes the pre-1.26.0 path.
        for product, members in _phase_products(phases):
            if len(members) == 1:
                name, frac = members[0]
                price = _phase_value(mineral_df, name, pgm_enrichment)
                if price is None:
                    continue
                yield name, frac, float(price)
                continue
            blended = _blend(members, lambda n: _phase_value(
                mineral_df, n, pgm_enrichment))
            if blended is None:
                continue
            yield product, blended[0], blended[1]
        return
    for frac_col, mineral_name in FRACTION_TO_MINERAL.items():
        frac = asteroid_row.get(frac_col)
        if frac is None or pd.isna(frac) or float(frac) <= 0.0:
            continue
        if mineral_name == "nickel-iron":
            price = _mineral_implied_value(mineral_df, mineral_name, pgm_enrichment)
        else:
            price = _mineral_implied_value(mineral_df, mineral_name)
        if price is None:
            continue
        yield mineral_name, float(frac), float(price)


def asteroid_bulk_value_usd_per_kg(
    asteroid_row: Row, mineral_df: pd.DataFrame,
) -> float:
    """Composite USD/kg for the bulk material of one asteroid.

    v1.17.6: memoised per composition: see `_composition_key`.  The walk below
    is unchanged and is still the only statement of the blend; this caches its
    answer.

    v1.3.4, applies per-asteroid PGM enrichment to the metal fraction.
    Module 1 v1.0.4+ provides `comp_pgm_enrichment` (default 1.0× chondritic
    baseline; 2.0× for differentiated M-type cores; 0.2× for V-type basaltic
    crust; 0.5× for mantle fragments).  Multiplies only the rare-metal yields
    in nickel-iron, base metals (Fe, Ni, Co) and non-metal categories
    (silicates, carbon, water) are unaffected.

    v1.3.3, "Other" residual mass (Module 1 fractions sum to less than 1
    in every type) was silently zero-valued; now treated as bulk silicate
    at $0.05/kg floor.
    """
    key = _composition_key(asteroid_row)
    if key is not None:
        entries = _composition_cache(mineral_df)
        hit = entries.get(key)
        if hit is not None and hit.bulk is not None:
            return hit.bulk

    pgm_enrichment = _pgm_enrichment(asteroid_row)

    total    = 0.0
    frac_sum = 0.0
    # v1.24.0: with phases, blend the phases instead of the four fractions.
    # `_phase_prices` skips a zero fraction where the four-fraction loop admits
    # one; a phase list carries no zeros, so the two agree on everything this
    # branch can be handed.
    with_phases = _row_phases(asteroid_row) is not None
    if with_phases:
        for _name, f, price in _phase_prices(asteroid_row, mineral_df):
            total    += f * price
            frac_sum += f
    for frac_col, mineral_name in (() if with_phases else FRACTION_TO_MINERAL.items()):
        frac = asteroid_row.get(frac_col)
        if frac is None or pd.isna(frac):
            continue
        # Only the metal-fraction → nickel-iron lookup is enrichment-sensitive
        # (PGMs ride in the metal phase).  Silicate / carbon / water yields
        # are unaffected by differentiation history.
        if mineral_name == "nickel-iron":
            price = _mineral_implied_value(mineral_df, mineral_name, pgm_enrichment)
        else:
            price = _mineral_implied_value(mineral_df, mineral_name)
        if price is None:
            continue
        f = float(frac)
        total    += f * float(price)
        frac_sum += f

    # Residual "other" mass; value at silicate floor so it doesn't vanish.
    if 0.0 < frac_sum < 1.0:
        other_frac     = 1.0 - frac_sum
        silicate_price = _mineral_price(mineral_df, "silicates") or 0.05
        total += other_frac * float(silicate_price)

    if key is not None:
        _composition_entry(entries, key).bulk = total
    return total


# ─── THE ONE PHASE STAGE 2 HAS NEVER HEARD OF  (v1.21.1) ─────────────────────
# `asteroid_phase_table` invents the composition residual, and Stage 2's mineral
# catalog has no row for it, so `markets.get(name)` missed and it took the
# infinite default: **priced at the `silicates` quote and bounded by nothing.**
#
# That is defect class 1 in market form -- a quantity with a price in one half
# of the model and no counterpart in the other -- and it hid for the same reason
# that class always hides.  Under the v1.14.0 demand curve every OTHER commodity
# in the haul was bounded, so the blended multiplier fell on every row anyway and
# the hole never showed as a hole.  A wall does not blend: a row whose bounded
# commodities all sit inside their ceilings feels nothing at all, and one
# unbounded phase is then the whole of a monotone-in-N objective.
#
# The alias is a MAPPING rather than a new market row on purpose.  The residual
# is not a commodity anybody trades; it is this module's name for "the rest of
# the rock", so inventing a Stage 2 row for it would put a fiction in the
# reference data.  Priced as silicates, bounded as silicates, in one place.
_RESIDUAL_PHASE = "other (bulk silicate)"
_PHASE_MARKET_ALIAS: Dict[str, str] = {_RESIDUAL_PHASE: "silicates"}


def phase_market_key(markets: Optional[Dict[str, float]], phase: str) -> str:
    """The MARKET a phase sells into, which is not always the phase's own name.

    v1.21.2.  `phase_market_kg` answers "how many kg/yr", and two phases can
    get the same answer for two different reasons: because they are the same
    market, or because they happen to have equal ceilings.  Only this function
    can tell those apart, and the difference is a whole allowance.

    ⚠️  IT TAKES `markets` FOR ONE REASON: TO RESOLVE THE ALIAS THE SAME WAY
    `phase_market_kg` DOES.  That function prefers a phase's OWN row and falls
    back to the alias, so a keyless version of this one would disagree with it
    the moment Stage 2 gained a row for an aliased phase -- pooling onto
    `silicates` while drawing a different ceiling.  Nothing today has both, and
    that is exactly when to make two functions agree by construction rather
    than by coincidence.

    🚨  THE ALIAS ABOVE MEANT "ONE SHARED CEILING" AND WAS IMPLEMENTED AS "A
    SECOND COPY OF IT".  v1.21.1 gave the composition residual the `silicates`
    ceiling it was already priced against, which was right, and every consumer
    then asked `phase_market_kg` per PHASE and got the full allowance twice --
    once for `silicates` and once for `other (bulk silicate)`.  The comment
    above already said "priced as silicates, bounded as silicates, in one
    place"; that was the intent, and the code gave each its own place.  The two
    co-occur on 100% of bodies and are a median 84% of the load, so this was
    not a corner.
    """
    if markets and phase in markets:
        return phase
    alias = _PHASE_MARKET_ALIAS.get(phase)
    return alias if alias is not None else phase


def phase_market_kg(markets: Optional[Dict[str, float]], phase: str) -> float:
    """Annual ceiling in kg/yr for one PHASE of the payload, or inf.

    The single place a phase name is turned into a market ceiling, so the
    alias above cannot be honoured at one call site and forgotten at another.
    Infinity is still the answer for a phase with no market and no alias, and
    that is deliberate: it means "nothing here bounds this", which the run
    banner reports rather than silently assuming a number.

    ⚠️  THIS IS A CEILING, NOT AN ENTITLEMENT.  Two phases sharing a market
    each get the same number back from here, and that is correct; what would
    be wrong is spending it twice.  Pair every call with `phase_market_key`
    and pool by that key.  See v1.21.2.
    """
    if not markets:
        return float("inf")
    hit = markets.get(phase)
    if hit is None:
        alias = _PHASE_MARKET_ALIAS.get(phase)
        hit = markets.get(alias) if alias is not None else None
    return float("inf") if hit is None else float(hit)


def asteroid_phase_table(
    asteroid_row: Row, mineral_df: pd.DataFrame,
) -> List[Tuple[str, float, float]]:
    """[(phase, mass_fraction, usd_per_kg)] for one asteroid (v1.6.0).

    The same four taxonomy fractions `asteroid_bulk_value_usd_per_kg` blends,
    but kept SEPARATE so a mission can choose what to load rather than being
    handed the mean.  The residual (Module 1's fractions sum to less than 1) is
    included as bulk silicate, matching the bulk function's floor treatment.

    Phases with zero fraction are dropped; you cannot select what is not
    there.

    v1.17.6: memoised per composition; see `_composition_key`.

    ⚠️  A COPY of the cached list is returned, deliberately.  Nothing in this
    module mutates a phase table, but v1.17.4 records the other half of that
    argument: handing a million rows one shared mutable object is a trap
    whether or not today's code springs it.  A copy also keeps the aliasing
    exactly as it is now; `_PHASE_ORDER_CACHE` is keyed on list IDENTITY, so
    one list per asteroid is what its single slot was measured against.  The
    copy is ~0.15 us against the ~14 us walk it replaces.
    """
    key = _composition_key(asteroid_row)
    if key is not None:
        entries = _composition_cache(mineral_df)
        hit = entries.get(key)
        if hit is not None and hit.phases is not None:
            return list(hit.phases)

    phases: List[Tuple[str, float, float]] = []
    frac_sum = 0.0
    for mineral_name, frac, price in _phase_prices(asteroid_row, mineral_df):
        phases.append((mineral_name, frac, price))
        frac_sum += frac

    if 0.0 < frac_sum < 1.0:
        # Composition fractions sum to less than 1; the remainder is undifferentiated
        # rock and is valued at the bulk-silicate floor.  ⚠️  It is priced at the
        # `silicates` QUOTE, which is why `_PHASE_MARKET_ALIAS` below must give it
        # the `silicates` CEILING: a phase that declares itself silicates for
        # price and not for quantity is priced in one half of the model and
        # unbounded in the other.
        silicate_price = _mineral_price(mineral_df, "silicates") or 0.05
        phases.append((_RESIDUAL_PHASE, 1.0 - frac_sum, float(silicate_price)))

    if key is not None:
        _composition_entry(entries, key).phases = list(phases)
    return phases


def saturation_price_multiplier(
    delivered_kg_per_yr: float,
    annual_market_kg:    float,
    elasticity:          float,
) -> float:
    """Price multiplier when a mission's output is material next to the market.

        P / P0 = (1 + Q_new / Q_market) ^ (−1/ε)

    Constant-elasticity demand.  Precious-metal demand is inelastic, 
    ε ≈ 0.5, so doubling world supply quarters the price, which is why
    "return a tonne of platinum" was never the business it looks like on a
    spot-price spreadsheet.  Returns 1.0 when the market swallows the
    quantity without noticing.
    """
    if annual_market_kg <= 0 or delivered_kg_per_yr <= 0 or elasticity <= 0:
        return 1.0
    ratio = delivered_kg_per_yr / annual_market_kg
    if ratio <= 1e-9:
        return 1.0
    return (1.0 + ratio) ** (-1.0 / elasticity)


# ─── CONSTANT PRICES AND A QUANTITY WALL  (v1.21.0) ──────────────────────────
def capacity_allowance_kg(
    annual_market_kg: float,
    n_missions:       int,
    fleet:            int,
    duration_yr:      float,
    cadence_yr:       float,
) -> float:
    """Kilograms of ONE commodity that ONE delivery may sell (v1.21.0).

    Under `market_model = "capacity_cap"` the price is flat at any volume and
    what bounds a programme is how much the destination can absorb while it
    waits.  So the question is not "what does the 400th tonne fetch" but "how
    long has the market been accumulating since the last delivery".

    ── The window ───────────────────────────────────────────────────────────

    A programme of F ships repeating every `cadence_yr` puts a delivery on the
    market every `cadence / F` years, so in steady state one delivery may sell
    `cap x cadence / F`.  Note that is the same constraint as a RATE test, seen
    from the other side:

        kg <= cap x cadence / F     <=>     kg x F / cadence <= cap

    The FIRST delivery is different, and it is the one exception this function
    makes.  Nothing has arrived yet, so the destination has been importing from
    Earth for the whole outbound-and-back trip: `duration_yr`, which is longer
    than the cadence, because the cadence is only the dig (or the window),
    while the duration is the whole mission.  Over a programme of N deliveries
    the market therefore accumulates for

        duration + (N - 1) x cadence / F

    years in total, and this returns the per-delivery average of that.  At
    N = 1 it is exactly `cap x duration`; as N grows it converges on the steady
    state `cap x cadence / F`.

    ⚠️  IT IS AVERAGED RATHER THAN BRANCHED, deliberately.  Giving delivery one
    the long window and every later delivery the short one is the same model,
    but as a step it puts a discontinuity between N = 1 and N = 2 that hands
    N = 1 a structural advantage no economics produced -- and the ladder would
    then collapse onto N = 1 for a reason that is a rule, not a result.  The
    average is continuous in N and gives the identical answer at both ends.

    ⚠️  `cadence_yr` and NOT `mission_duration_yr` sets the steady state, which
    is a change from the v1.14.0 elasticity term.  That term divided by the
    mission duration, but a rig starts its next campaign as soon as the feed is
    out of the ground; `campaign_cadence_yr` is the interval that actually
    repeats.  Since the duration exceeds the cadence on essentially every body,
    the old denominator UNDERSTATED sustained throughput.  Under a smooth curve
    that is a bias buried in an exponent; under a wall it moves the feasible
    fleet directly, so it stops being ignorable.

    An infinite ceiling (a commodity with no `annual_market_kg` entry, which is
    every bulk commodity and everything sold at `earth_surface`) returns inf
    and nothing ever binds, which is the documented degenerate case rather than
    an oversight.
    """
    cap = float(annual_market_kg)
    if cap <= 0.0:
        return 0.0
    window = _delivery_window_yr(n_missions, fleet, duration_yr, cadence_yr)
    if window <= 0.0:
        return 0.0
    return cap * window


def _delivery_window_yr(
    n_missions: int, fleet: int, duration_yr: float, cadence_yr: float,
) -> float:
    """Years of market accumulation behind ONE delivery of a programme.

    The single statement of the window algebra `capacity_allowance_kg`
    documents.  Split out because the ladder needs the window ONCE per rung and
    then multiplies it by each commodity's own ceiling; calling the per-
    commodity function would re-derive the same five float operations for every
    phase in the haul, ~60 of them per rung and ~40 rungs per candidate.

    Two readers, one derivation.  Writing the expression out again at the call
    site is exactly the "two copies of one algebra drifting apart" hazard the
    mass ledger warns about.
    """
    n      = max(1, int(n_missions))
    f      = max(1, int(fleet))
    first  = max(0.0, float(duration_yr))
    steady = max(0.0, float(cadence_yr)) / f
    return (first + (n - 1) * steady) / n


def _capped_sale_value(
    sale_terms: List[Tuple[float, float, float, str]], window_yr: float,
    surplus_price_frac: float = 0.0,
) -> Tuple[float, float, float]:
    """`(value_usd, unsold_kg, surplus_kg)`, commodities clipped at the ceiling.

    Each kilogram inside the ceiling fetches the full price the mineral catalog
    quotes.  What happens to the kilograms past it is v1.22.0's
    `sell_surplus_at_discount`, and the two answers are reported in different
    columns because they are different events:

      surplus_price_frac = 0.0   a quantity WALL.  The surplus earns nothing
                                 and comes back as `unsold_kg`.  v1.21.0's
                                 model, and what the 2026-09 campaign measured.
      surplus_price_frac > 0.0   the surplus SELLS, at that fraction of the
                                 full price, and comes back as `surplus_kg`
                                 with `unsold_kg` at 0.0.

    ⚠️  ONE MEANING PER COLUMN, and that is why this returns three floats
    rather than reusing `unsold_kg` for both.  Mass that earned nothing and
    mass that earned half are not the same measurement, and a harness that
    counted "unsold" across the flip would have silently changed what it was
    counting -- which is the diagnostic-changes-meaning-under-you failure this
    module has now hit twice.

    ⚠️  Accumulates over `sale_terms` in its own insertion order, exactly as
    the elasticity branch does, and for the same reason: floating-point
    addition is not associative and every verification in this project is a
    bit-identity check.  See the warning in `optimal_payload_mix`.

    Used for the RAW cargo, where the mix is the body's own composition and
    cannot be reshaped.  A beneficiated load goes through `optimal_payload_mix`
    with the same ceilings instead, which spends the freed hold space on the
    next most valuable phase rather than flying the excess unsold -- and, since
    v1.22.0, weighs that against carrying the surplus at the discount.

    🚨  v1.21.2: THE ALLOWANCE IS POOLED PER MARKET, NOT PER PHASE.  Each entry
    carries the market KEY it sells into, and phases sharing a key draw down
    one shared allowance.  Before this the `silicates` phase and the
    composition residual each got the full silicates ceiling, which is one
    market sold twice, on 100% of bodies.

    ⚠️  Insertion order decides WHICH phase is recorded as unsold when a pooled
    allowance runs out.  It does not change `value`, because the only pair that
    shares a key today is priced identically by construction -- the residual is
    priced at the silicates quote.  If a future alias ever joins two phases at
    DIFFERENT prices, this loop would need to spend the allowance on the dearer
    one first, and the order it happens to receive would stop being good
    enough.
    """
    value   = 0.0
    unsold  = 0.0
    surplus = 0.0
    sells   = surplus_price_frac > 0.0
    remaining: Dict[str, float] = {}
    for kg, price, mkt, key in sale_terms:
        allowance = remaining.get(key)
        if allowance is None:
            allowance = mkt * window_yr
        if kg > allowance:
            over = kg - allowance
            value += allowance * price
            if sells:
                # v1.22.0.  The surplus is carried and sold, at a discount.
                # Written as a second term rather than folded into one blended
                # price so the wall's arithmetic is untouched when the flag is
                # off: at `sells` False not one float below differs from
                # v1.21.2, which is what lets the campaign's cells reproduce.
                value   += over * price * surplus_price_frac
                surplus += over
            else:
                unsold  += over
            remaining[key] = 0.0
        else:
            value += kg * price
            remaining[key] = allowance - kg
    return value, unsold, surplus


# Single-slot memo for the knapsack's price ordering (v1.14.2).  The phase table
# is built once per asteroid and never mutated, but `optimal_payload_mix` is
# called ~2,100 times per asteroid in a beneficiated run and re-sorted it every
# time: 325,000 `sorted()` calls plus 1.4 million key-lambda calls per 150
# rows, all re-deriving the same order for the same rock.
#
# Same shape and the same justification as `_OPS_CACHE` below: keyed by object
# identity, with the list itself held in the slot so its id cannot be recycled
# onto a different object, and single-slot rather than a growing dict so a
# long-lived session cannot leak.  A caller that mutates a phase list IN PLACE
# rather than rebinding would read a stale order; nothing in this module does,
# and `asteroid_phase_table` returns a fresh list per asteroid.
#
# ⚠️  What this deliberately does NOT do is sort the phase table at source.  See
# the warning in `optimal_payload_mix`; the table's natural order is
# load-bearing elsewhere, on the last ULP.
_PHASE_ORDER_CACHE: Tuple[Optional[List[Tuple[str, float, float]]],
                          List[Tuple[str, float, float]]] = (None, [])


def optimal_payload_mix(
    payload_kg: float,
    feed_kg:    float,
    phases:     List[Tuple[str, float, float]],
    recovery:   float,
    want_phase: Optional[str] = None,
    caps:       Optional[Dict[str, float]] = None,
    cap_keys:   Optional[Dict[str, str]]   = None,
    surplus_price_frac: float = 0.0,
) -> Union[Dict[str, object], float]:
    """Most valuable payload obtainable from `feed_kg` of this rock (v1.6.0).

    The mission is not sent for a named mineral; it is sent to bring back the
    best load it can assemble from what the target actually contains.  With a
    fixed mass budget and divisible, per-kilogram-priced phases, that is a
    FRACTIONAL KNAPSACK, and greedy selection by $/kg is provably optimal:
    fill the hold with the most valuable phase available, then the next, until
    the hold is full or the feed runs out.

    Separation recovers `recovery` of each phase present in the feed; whatever
    is not loaded is left at the asteroid.

    Returns value, blended $/kg, the chosen mix in kg, the mass fraction the
    best phase makes up, which is the natural read on how well concentrated
    the load actually is, and `surplus_kg`, the mass of that load sold past a
    market ceiling at the discount (v1.22.0; 0.0 on every other path).

    ⚠️  **Do not "fix" this by sorting the phase table at source.**  The greedy
    order is needed HERE and nowhere else, and `phases` arrives in its natural
    (Module 1 fraction) order because the market-saturation block in
    `_evaluate_combo_at_ratio` builds `sold` from it and then accumulates
    `adj_value` by iterating that dict.  Floating-point addition is not
    associative, so reordering the table reorders that sum and moves
    `saturation_multiplier`, `gross_value_usd`, `profit_usd`, `roi` and
    `delivered_value_usd_per_kg` in their last bit.

    Measured, on a 150-row beneficiated cislunar sample: max relative change
    2.8e-16 on 3 of 60 rows, and no vehicle, propellant, concentration ratio or
    power source moved.  Numerically that is nothing.  It is still fatal, because
    every verification this project relies on is a bit-identity check: the
    sha256 CSV diffs, `max |error| 0.000000000 kg`, "124 of 124 columns
    identical".  A sort at source reads like a free cleanup and silently costs
    you the ability to prove a release changed nothing.

    So the ordering is memoised per phase list instead, which leaves the table
    itself untouched.

    ── `want_phase` (v1.17.1) ───────────────────────────────────────────────
    Returns the kilograms of ONE named phase that the greedy walk loads, as a
    bare float, instead of the full result dict.  `_cargo_water_kg` is 97% of
    this function's callers and reads exactly one key, `mix_kg["water"]`, 
    so it was paying for the mix dict, the value accumulation and the
    dominant-phase `max()` over `mix.items()` on every call, then throwing all
    three away.

    It is a short circuit, NOT a second knapsack: the walk below is the only
    statement of the greedy algebra in this module, and `want_phase` only
    decides how much of each pass's result is kept and when to stop.  Writing
    it as a separate water-only function would have been the "two copies of
    this algebra drifting apart" hazard that the mass ledger warns about, for
    no extra speed; the loop is not what costs, the bookkeeping is.

    The answer is bit-identical by construction rather than by measurement:
    `remaining` is decremented in the same order by the same `min`, and the
    take for the requested phase is returned before anything downstream of it
    could perturb it.  Verified anyway; see the release notes.

    ── `caps` (v1.21.0) ─────────────────────────────────────────────────────
    An optional per-phase UPPER BOUND in kilograms, which is what
    `market_model = "capacity_cap"` uses to say how much of each commodity the
    destination can take while it waits.  See `capacity_allowance_kg`.

    ✅  GREEDY IS STILL PROVABLY OPTIMAL.  Per-item quantity limits turn an
    unbounded fractional knapsack into a BOUNDED one, and the bounded form is
    solved exactly by the same walk: sort by $/kg descending and take
    `min(available, allowance, remaining)` of each in turn.  So this is not a
    clamp bolted onto the outside of an optimiser -- which is the shape this
    module warns against, because the content and purity bounds are supposed to
    FALL OUT of the knapsack rather than be re-imposed on it -- it is the
    correct formulation of the same problem with one more constraint.

    The freed hold space is what the caller actually wanted: a load that caps
    out on iron keeps walking down the price order and spends the remaining
    capacity on whatever is next, rather than flying the excess unsold.

    🚨  v1.21.2: `caps` IS KEYED BY MARKET AND IS CONSUMED IN PLACE.  Pass a
    dict you own; this walk decrements it.  Keying it by phase gave two phases
    that sell into one market the full allowance each, which is the defect
    v1.21.2 exists to close, and consuming it is what makes the pool shared
    rather than merely shared-looking.

    `cap_keys` maps a phase name to the market key its allowance lives under,
    and a phase missing from it stands alone.  It is a MAP rather than a call
    to `phase_market_key` here because that function needs the market table to
    resolve an alias the way `phase_market_kg` does, and handing the knapsack
    the whole of Stage 2 to look up five strings would be the wrong seam: the
    caller already knows both, and resolving it there keeps the two lookups
    agreeing in one place.

    ── `surplus_price_frac` (v1.22.0) ───────────────────────────────────────
    What a kilogram past a ceiling fetches, as a fraction of the full price.
    0.0 is v1.21.0's wall: the allowance is a hard upper bound and anything
    past it is simply not loaded.  Above 0.0 the surplus becomes cargo the
    load may CHOOSE to carry, and the knapsack has to decide whether it is
    worth the hold space.

    ✅  GREEDY IS STILL EXACT, and the formulation is the standard one: a
    two-step price schedule is two ITEMS, not a clamp.  Each phase enters the
    walk twice, once at `price` limited by its market allowance and once at
    `price x surplus_price_frac` limited by what is left of the feed, and the
    merged list is sorted by unit price like any other fractional knapsack.
    Every item still has a constant unit value and is divisible, which is the
    only condition greedy needs.

    🚨  THE INTERLEAVING IS THE POINT, and it is why this cannot be done as a
    second pass over the leftovers.  A rich phase's HALF-PRICE surplus can be
    worth more per kilogram than a poor phase's full-price allowance, and when
    it is, the optimal load carries it instead.  Filling the hold with
    everything full-price first and topping up with surplus afterwards is a
    different, strictly worse load; it would also be the "clamp bolted onto
    the outside of an optimiser" shape this docstring warns against three
    paragraphs up.

    ⚠️  ONE WALK, not two.  The tiered sequence is built ahead of the loop and
    the loop below is unchanged for everyone else: `tier_taken` is None on
    every call that is not tiered, so the default path pays one `is None` test
    per phase and no arithmetic.  A second copy of this walk is the hazard the
    `want_phase` note above is about, and it would be a worse one here, because
    this is the copy that decides what a load is worth.

    ⚠️  Tiers are OFF whenever `want_phase` is set, deliberately.  That short
    circuit returns the first take of the named phase and stops, which would
    report the allowance and miss the surplus.  It is not a live combination:
    `want_phase` belongs to `_cargo_water_kg`, on the SIZING path, and the
    sizing path must never pass `caps` at all -- see the warning below.

    ⚠️  `caps=None` must stay bit-identical to the pre-v1.21.0 walk, because
    the `elasticity` market model is the v1.14.0 curve, and it reproduced
    v1.14.0 to v1.20.0 exactly until v1.21.1's residual-ceiling fix moved the
    two raw cells.  The guard below adds
    a branch and no arithmetic; when `caps` is None not one float differs.

    ⚠️  AND THE SIZING PATH MUST NEVER PASS CAPS.  `_cargo_water_kg` calls this
    from inside the fixed-point power solve, so a cap reaching it would make
    the whole MASS cascade a function of fleet size -- the one asymmetry that
    makes the programme ladder affordable to search at all.  Ceilings bound
    what a load may SELL, not what the rig digs or the hull carries; the plant
    is sized for the load the body can assemble and the ship is designed once
    for a fleet that is sized around it.  That runs conservative (the array is
    sized for a richer mix than a capped delivery carries), which is the safe
    direction, and it keeps the ledger internally consistent: the array flown
    is still exactly the array charged.
    """
    if payload_kg <= 0 or not phases:
        return 0.0 if want_phase is not None else {
            "value_usd": 0.0, "usd_per_kg": 0.0, "mix_kg": {},
            "dominant_phase": None, "dominant_frac": 0.0,
            "surplus_kg": 0.0}

    global _PHASE_ORDER_CACHE
    if _PHASE_ORDER_CACHE[0] is not phases:
        _PHASE_ORDER_CACHE = (phases, sorted(phases, key=lambda p: -p[2]))
    by_price = _PHASE_ORDER_CACHE[1]

    # v1.22.0.  The tiered sequence, built only when a surplus can actually be
    # sold.  `tier_taken` doubles as the mode flag and as the per-phase ledger
    # the second tier needs: a phase's discounted tier may only draw on the
    # feed its full-price tier left behind, and the sort guarantees the
    # full-price tier is reached first: same phase, strictly higher unit price,
    # and at `surplus_price_frac == 1.0` the two tie and a stable sort settles
    # it in insertion order, which is full-price first by construction.
    #
    # Not cached: this list depends on the fraction as well as the phase table,
    # it is built once per (programme rung x candidate) rather than per call
    # like `by_price`, and the capped branch is already the rare one -- the
    # ladder's fast path proves nothing binds before ever arriving here.
    tier_taken: Optional[Dict[str, float]] = None
    walk = by_price
    if caps is not None and surplus_price_frac > 0.0 and want_phase is None:
        # Clamped HERE as well as at the resolver that normally feeds it and
        # at `market_config_check`, because this is where the ASSUMPTION lives:
        # above 1.0 the discounted tier would sort ahead of the full-price one,
        # take the market allowance, and make the capped load worth more than
        # the uncapped one.  One min() per tiered build, not per item, and the
        # branch is the rare one.
        frac = surplus_price_frac if surplus_price_frac < 1.0 else 1.0
        tiered: List[Tuple[str, float, float]] = []
        for p_name, p_frac, p_price in by_price:
            tiered.append((p_name, p_frac, p_price))
            tiered.append((p_name, p_frac, p_price * frac))
        tiered.sort(key=lambda p: -p[2])
        walk       = tiered
        tier_taken = {}

    remaining  = float(payload_kg)
    total      = 0.0
    surplus_kg = 0.0
    mix: Dict[str, float] = {}
    for name, frac, price in walk:
        if remaining <= 0:
            break
        # `full_tier` is "this phase has not been reached yet", which is the
        # same question as "this is its full-price tier" by the ordering above.
        # Only the full-price tier draws on a market allowance; the surplus is
        # by definition the part no allowance covers.
        if tier_taken is None:
            available = float(feed_kg) * frac * recovery
            full_tier = True
            had       = 0.0
        else:
            had       = tier_taken.get(name, -1.0)
            full_tier = had < 0.0
            if full_tier:
                had       = 0.0
                available = float(feed_kg) * frac * recovery
            else:
                available = float(feed_kg) * frac * recovery - had
        take      = min(available, remaining)
        if caps is not None and full_tier:
            # v1.21.0.  The bounded-knapsack step.  Clipping `take` and NOT
            # `remaining` is the whole point: the hold space this phase does
            # not get stays available to the next one down the price order.
            #
            # v1.21.2: `caps` is keyed by MARKET, not by phase, and is drawn
            # down as it is spent, so two phases sharing a market share one
            # allowance.  The walk is in descending price order, so the dearer
            # phase draws first, which is the right way to spend a scarce
            # allowance and is why this needs no separate ordering rule.
            key = cap_keys.get(name, name) if cap_keys else name
            allowance = caps.get(key)
            if allowance is not None:
                if allowance < take:
                    take = allowance
                caps[key] = allowance - take
        if tier_taken is not None:
            # Recorded BEFORE the `take <= 0` skip below, and that ordering is
            # load-bearing: a full-price tier whose allowance was already spent
            # takes nothing, and if it went unrecorded its own surplus tier
            # would be read as the full-price one and clipped at the same
            # exhausted allowance -- so the discount would silently never fire
            # on exactly the phases it exists for.
            tier_taken[name] = had + take
        if take <= 0:
            continue
        if want_phase is not None:
            # The caller wants one number.  Stop as soon as it is known;
            # nothing after this point in the walk can change it.
            if name == want_phase:
                return take
            remaining -= take
            continue
        if full_tier:
            mix[name] = take
        else:
            # The same phase, loaded twice at two prices.  `mix_kg` is a mass
            # ledger and must stay one entry per phase; `surplus_kg` is what
            # says how much of it sold at the discount.
            mix[name]   = mix.get(name, 0.0) + take
            surplus_kg += take
        total     += take * price
        remaining -= take

    if want_phase is not None:
        # Never reached in the walk: the hold filled before this phase came up,
        # or the feed had none of it.  `mix_kg.get(want_phase, 0.0)` in the full
        # path returns the same 0.0, including when `loaded <= 0` below would
        # have short-circuited to an empty mix.
        return 0.0

    # Anything the feed could not fill is dead space, the hold flies partly
    # empty rather than being topped up with rock that was never dug.
    loaded = float(payload_kg) - remaining
    if loaded <= 0:
        return {"value_usd": 0.0, "usd_per_kg": 0.0, "mix_kg": {},
                "dominant_phase": None, "dominant_frac": 0.0,
                "surplus_kg": 0.0}

    dominant = max(mix.items(), key=lambda kv: kv[1])
    return {
        "value_usd":      total,
        "usd_per_kg":     total / loaded,
        "loaded_kg":      loaded,
        "mix_kg":         mix,
        "surplus_kg":     surplus_kg,
        "dominant_phase": dominant[0],
        "dominant_frac":  dominant[1] / loaded,
    }


def asteroid_best_phase_usd_per_kg(
    asteroid_row: Row, mineral_df: pd.DataFrame,
) -> float:
    """$/kg of the single most valuable phase actually present (v1.5.0).

    This is the PURITY BOUND on beneficiation.  Concentrating rejects gangue,
    it does not transmute: the richest concentrate physically obtainable from
    a body is 100% of its best phase, so no amount of processing can push the
    delivered $/kg above this number.

    Only phases with a non-zero fraction count; a body with no metal cannot
    be concentrated into metal.  Returns the bulk value as a floor so the
    bound can never sit below the unconcentrated material.

    v1.17.6: memoised per composition; see `_composition_key`.  This is the
    most expensive of the three at 27.7 us/row, because it walks the phases AND
    calls the bulk function, so a beneficiated run derived the bulk blend twice
    per asteroid.
    """
    key = _composition_key(asteroid_row)
    if key is not None:
        entries = _composition_cache(mineral_df)
        hit = entries.get(key)
        if hit is not None and hit.best is not None:
            return hit.best

    best = 0.0
    for _mineral_name, _frac, price in _phase_prices(asteroid_row, mineral_df):
        if price > best:
            best = price

    bulk = asteroid_bulk_value_usd_per_kg(asteroid_row, mineral_df)
    value = max(best, bulk)
    if key is not None:
        # Re-read the cache: the bulk call above may have created the entry.
        _composition_entry(_composition_cache(mineral_df), key).best = value
    return value
