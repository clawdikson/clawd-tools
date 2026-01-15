"""Tests for search functionality - fuzzy scoring algorithm."""

import pytest


class TestFuzzyScore:
    """Tests for fuzzy search scoring algorithm."""

    def test_exact_match_at_start(self):
        """Test exact substring match at start gets highest score."""
        from tools.sqlitefs_explorer.widgets.search import fuzzy_score
        score = fuzzy_score("search", "search/results/file.json")
        assert score > 0.9

    def test_exact_match_later(self):
        """Test exact match later in string gets lower but good score."""
        from tools.sqlitefs_explorer.widgets.search import fuzzy_score
        score = fuzzy_score("file", "path/to/file.json")
        assert 0.5 < score < 1.0

    def test_consecutive_match_bonus(self):
        """Test that consecutive character matches get bonus."""
        from tools.sqlitefs_explorer.widgets.search import fuzzy_score
        # "search" matches better than "s_e_a_r_c_h"
        score_consecutive = fuzzy_score("abc", "abc_def")
        score_scattered = fuzzy_score("abc", "a_b_c_def")
        assert score_consecutive > score_scattered

    def test_no_match(self):
        """Test that non-matching query returns 0."""
        from tools.sqlitefs_explorer.widgets.search import fuzzy_score
        score = fuzzy_score("xyz", "abc")
        assert score == 0.0

    def test_partial_match(self):
        """Test partial character match."""
        from tools.sqlitefs_explorer.widgets.search import fuzzy_score
        score = fuzzy_score("sear", "search/results")
        assert score > 0

    def test_case_sensitivity(self):
        """Test that scoring is case-insensitive by default."""
        from tools.sqlitefs_explorer.widgets.search import fuzzy_score
        # Query should be lowercase already
        score_lower = fuzzy_score("search", "search/results")
        score_upper = fuzzy_score("search", "SEARCH/RESULTS".lower())
        assert score_lower == score_upper

    def test_empty_query(self):
        """Test empty query returns 0."""
        from tools.sqlitefs_explorer.widgets.search import fuzzy_score
        score = fuzzy_score("", "some/path")
        assert score == 0.0

    def test_empty_target(self):
        """Test empty target returns 0."""
        from tools.sqlitefs_explorer.widgets.search import fuzzy_score
        score = fuzzy_score("query", "")
        assert score == 0.0


class TestContentMatch:
    """Tests for JSON content matching algorithm."""

    def test_match_key(self):
        """Test matching JSON key."""
        from tools.sqlitefs_explorer.widgets.search import content_matches
        obj = {"npi": "1234567890", "name": "Dr. Smith"}
        assert content_matches("npi", obj, search_type="key") is True
        assert content_matches("address", obj, search_type="key") is False

    def test_match_value(self):
        """Test matching JSON value."""
        from tools.sqlitefs_explorer.widgets.search import content_matches
        obj = {"npi": "1234567890", "name": "Dr. Smith"}
        assert content_matches("smith", obj, search_type="value") is True
        assert content_matches("jones", obj, search_type="value") is False

    def test_match_any(self):
        """Test matching either key or value."""
        from tools.sqlitefs_explorer.widgets.search import content_matches
        obj = {"npi": "1234567890", "name": "Dr. Smith"}
        assert content_matches("npi", obj, search_type="any") is True
        assert content_matches("smith", obj, search_type="any") is True

    def test_match_nested_dict(self):
        """Test matching in nested dictionary."""
        from tools.sqlitefs_explorer.widgets.search import content_matches
        obj = {
            "provider": {
                "npi": "1234567890",
                "address": {"city": "Chicago"}
            }
        }
        assert content_matches("chicago", obj, search_type="value") is True
        assert content_matches("city", obj, search_type="key") is True

    def test_match_list(self):
        """Test matching in list."""
        from tools.sqlitefs_explorer.widgets.search import content_matches
        obj = {"locations": [{"city": "Chicago"}, {"city": "Springfield"}]}
        assert content_matches("springfield", obj, search_type="value") is True

    def test_match_case_insensitive(self):
        """Test matching is case insensitive."""
        from tools.sqlitefs_explorer.widgets.search import content_matches
        obj = {"Name": "Dr. SMITH"}
        assert content_matches("smith", obj, search_type="value") is True
        assert content_matches("name", obj, search_type="key") is True

    def test_match_depth_limit(self):
        """Test that matching respects depth limit."""
        from tools.sqlitefs_explorer.widgets.search import content_matches
        # Create deeply nested object
        obj = {"l1": {"l2": {"l3": {"l4": {"l5": {"l6": {"l7": {"l8": {"l9": {"l10": {"l11": {"deep": "value"}}}}}}}}}}}}
        # With depth limit of 10, should not find "deep" or "value"
        assert content_matches("deep", obj, search_type="key") is False

    def test_match_number_as_string(self):
        """Test matching number values as strings."""
        from tools.sqlitefs_explorer.widgets.search import content_matches
        obj = {"count": 1234}
        assert content_matches("1234", obj, search_type="value") is True

    def test_match_in_list_strings(self):
        """Test matching in list of strings."""
        from tools.sqlitefs_explorer.widgets.search import content_matches
        obj = {"tags": ["healthcare", "provider", "npi"]}
        assert content_matches("provider", obj, search_type="value") is True
