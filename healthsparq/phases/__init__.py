"""
HealthSparq Phase Execution Modules.

Contains the phase execution functions for the scraper pipeline:
- Phase 1 (search): Provider discovery
- Phase 2 (details): Detail extraction
- Phase 3 (normalize): Data normalization and deduplication
"""

from .details import (
    DetailsConfig,
    DetailsResult,
    run_details,
    run_details_sync,
)
from .normalize import (
    NormalizeConfig,
    NormalizeResult,
    run_normalize,
    run_normalize_sync,
)
from .search import (
    SearchConfig,
    SearchResult,
    CountySearchResult,
    run_search,
    run_search_sync,
)

__all__ = [
    # Search phase
    "SearchConfig",
    "SearchResult",
    "CountySearchResult",
    "run_search",
    "run_search_sync",
    # Details phase
    "DetailsConfig",
    "DetailsResult",
    "run_details",
    "run_details_sync",
    # Normalize phase
    "NormalizeConfig",
    "NormalizeResult",
    "run_normalize",
    "run_normalize_sync",
]
