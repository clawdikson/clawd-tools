"""
Sapphire Package - Scalable Scraping Library for ProviderFinderOnline Sites.

Consolidates 15 Sapphire site implementations into a shared library.

Usage:
    CLI:
        python -m sapphire run molina --curr 20251230
        python -m sapphire list

    Library:
        from sapphire import run_scraper_sync, load_config

        config = load_config("molina")
        result = run_scraper_sync(config, curr_date="20251230")
"""

from sapphire.config.loader import load_config
from sapphire.config.schema import SapphireProjectConfig
from sapphire.api import run_scraper_sync, run_scraper_async, ScraperResult

__version__ = "1.0.0"
__all__ = [
    # Configuration
    "load_config",
    "SapphireProjectConfig",
    # API
    "run_scraper_sync",
    "run_scraper_async",
    "ScraperResult",
]
