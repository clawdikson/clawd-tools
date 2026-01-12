"""Search utilities for SQLiteFS Explorer.

Contains fuzzy path search and content search algorithms.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class SearchResult:
    """A search result with path and match score.

    Attributes:
        path: File path
        score: Match score (0-1, higher is better)
        is_dir: Whether path is a directory
    """

    path: str
    score: float
    is_dir: bool


def fuzzy_score(query: str, target: str) -> float:
    """Calculate fuzzy match score between query and target.

    Scoring:
    - Exact substring match at start: highest score (1.0)
    - Exact substring match later: good score (0.5-1.0)
    - Character-by-character match: lower score
    - Consecutive character matches get bonus

    Args:
        query: Search query (should be lowercase)
        target: Target string to match against (should be lowercase)

    Returns:
        Score from 0.0 to 1.0, where higher is better match
    """
    if not query or not target:
        return 0.0

    # Exact substring match - best case
    if query in target:
        pos = target.index(query)
        # Higher score for matches at start
        return 1.0 - (pos / len(target)) * 0.5

    # Character-by-character fuzzy match
    query_idx = 0
    score = 0.0
    last_match_pos = -1

    for i, char in enumerate(target):
        if query_idx < len(query) and char == query[query_idx]:
            # Bonus for consecutive matches
            if last_match_pos == i - 1:
                score += 0.2
            else:
                score += 0.1
            last_match_pos = i
            query_idx += 1

    # Only return score if all query chars matched
    if query_idx == len(query):
        return score / len(query)

    return 0.0


def content_matches(
    query: str,
    obj: dict | list | str | int | float | bool | None,
    search_type: Literal["key", "value", "any"] = "any",
    depth: int = 0,
    max_depth: int = 10,
) -> bool:
    """Check if query matches object keys/values.

    Args:
        query: Search query (case-insensitive)
        obj: JSON object to search in
        search_type: "key" for keys only, "value" for values, "any" for both
        depth: Current recursion depth
        max_depth: Maximum recursion depth to prevent infinite loops

    Returns:
        True if query matches, False otherwise
    """
    if depth > max_depth:
        return False

    query_lower = query.lower()

    if isinstance(obj, dict):
        for key, value in obj.items():
            # Check key
            if search_type in ("key", "any"):
                if query_lower in str(key).lower():
                    return True

            # Check string values
            if search_type in ("value", "any"):
                if isinstance(value, str) and query_lower in value.lower():
                    return True
                # Check non-dict/list values as strings
                if not isinstance(value, (dict, list)) and value is not None:
                    if query_lower in str(value).lower():
                        return True

            # Recurse into nested structures
            if isinstance(value, (dict, list)):
                if content_matches(query, value, search_type, depth + 1, max_depth):
                    return True

    elif isinstance(obj, list):
        for item in obj:
            if content_matches(query, item, search_type, depth + 1, max_depth):
                return True

    elif search_type in ("value", "any"):
        # Check primitive values
        if obj is not None and query_lower in str(obj).lower():
            return True

    return False
