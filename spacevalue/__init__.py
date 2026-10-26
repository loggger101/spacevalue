# -*- coding: utf-8 -*-
"""spacevalue: what a kilogram of asteroid material is worth, and where.

One table per delivery destination (Earth's surface, LEO, GTO, GEO, a
cislunar depot, the lunar surface, Mars orbit, the Mars surface), pricing
every mineral and element an asteroid composition can name.  A commodity sold
on Earth is worth its market price; one sold in space is worth the launch it
saves there, or its Earth price less the trip down, whichever is more.

    >>> import spacevalue
    >>> cfg = spacevalue.MineralValueConfig(delivery_destination="cislunar",
    ...                                     quote_snapshot="metals-2026-10-07")
    >>> table = spacevalue.build_mineral_value_catalog(cfg)

Metal prices come from recorded quote snapshots by default in every published
release, so the same release is the same bytes on every run.  Live prices are
opt-in (`use_yfinance=True`, extra `spacevalue[live]`).

This was Stage 2 of economicspace (https://github.com/loggger101/economicspace)
until its data contract 1.16.0.  The delivery chains and the launch price it
prices with come from spacecost (https://github.com/loggger101/spacecost).
"""

from .catalog import (ANNUAL_WORLD_PRODUCTION_KG, CONFIG, DELIVERY_DESTINATIONS,
                      IN_SPACE_ANNUAL_DEMAND_KG, IN_SPACE_UTILITY,
                      IN_SPACE_UTILITY_BY_DESTINATION, MINERAL_REFERENCE,
                      QUOTES_DIR, MineralValueConfig, annual_market_kg,
                      apply_delivery_destination, build_mineral_value_catalog,
                      fetch_metals_dev, fetch_reference_table, fetch_yfinance,
                      in_space_price_usd_per_kg, in_space_utility,
                      load_metal_snapshot, lookup_mineral, merge_sources,
                      metal_prices_from_quotes, metal_tickers,
                      mineral_to_element_value, snapshot_metal_prices,
                      validate, value_for_destination, value_per_kg)
from .release import (ASSET_MANIFEST, build_release, check_release,
                      table_filename)

# The PACKAGE release.  Not the data contract: that is
# `MineralValueConfig.pipeline_version`, stamped into every row.
__version__ = "0.1.0"

# The DATA contract this release writes, read off the config (the authority).
DATA_VERSION = CONFIG.pipeline_version

__all__ = [
    "__version__", "DATA_VERSION",
    "CONFIG", "MineralValueConfig", "QUOTES_DIR",
    "MINERAL_REFERENCE", "DELIVERY_DESTINATIONS",
    "IN_SPACE_UTILITY", "IN_SPACE_UTILITY_BY_DESTINATION",
    "IN_SPACE_ANNUAL_DEMAND_KG", "ANNUAL_WORLD_PRODUCTION_KG",
    "build_mineral_value_catalog", "validate",
    "fetch_yfinance", "fetch_metals_dev", "fetch_reference_table",
    "metal_tickers", "metal_prices_from_quotes", "load_metal_snapshot",
    "snapshot_metal_prices", "merge_sources", "apply_delivery_destination",
    "in_space_utility", "in_space_price_usd_per_kg", "annual_market_kg",
    "value_for_destination",
    "lookup_mineral", "value_per_kg", "mineral_to_element_value",
    "build_release", "check_release", "table_filename", "ASSET_MANIFEST",
]
