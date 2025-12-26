"""Tests for compare_outputs module."""

import tempfile
from pathlib import Path

import orjson
import pytest

from healthsparq.tests.compare_outputs import (
    compare_counts,
    compare_npis,
    compare_schemas,
    get_all_keys,
    get_schema_fields,
    load_jsonl,
    validate_deduplication,
)


class TestGetAllKeys:
    def test_flat_dict(self):
        d = {"a": 1, "b": 2}
        keys = get_all_keys(d)
        assert keys == {"a", "b"}

    def test_nested_dict(self):
        d = {"a": {"b": 1, "c": 2}}
        keys = get_all_keys(d)
        assert "a" in keys
        assert "a.b" in keys
        assert "a.c" in keys

    def test_list_of_dicts(self):
        d = {"items": [{"x": 1}]}
        keys = get_all_keys(d)
        assert "items" in keys
        assert "items[].x" in keys


class TestCompareSchemas:
    def test_matching_schemas(self):
        legacy = {"a", "b", "c"}
        singleton = {"a", "b", "c"}
        result = compare_schemas(legacy, singleton)
        assert result["match"] is True
        assert result["legacy_only"] == []
        assert result["singleton_only"] == []

    def test_mismatched_schemas(self):
        legacy = {"a", "b"}
        singleton = {"b", "c"}
        result = compare_schemas(legacy, singleton)
        assert result["match"] is False
        assert "a" in result["legacy_only"]
        assert "c" in result["singleton_only"]


class TestCompareCounts:
    def test_exact_match(self):
        legacy = [1, 2, 3]
        singleton = [1, 2, 3]
        result = compare_counts(legacy, singleton, 0.99)
        assert result["ratio"] == 1.0
        assert result["within_threshold"] is True

    def test_within_threshold(self):
        legacy = list(range(100))
        singleton = list(range(99))
        result = compare_counts(legacy, singleton, 0.99)
        assert result["ratio"] == 0.99
        assert result["within_threshold"] is True

    def test_below_threshold(self):
        legacy = list(range(100))
        singleton = list(range(90))
        result = compare_counts(legacy, singleton, 0.99)
        assert result["ratio"] == 0.90
        assert result["within_threshold"] is False


class TestCompareNpis:
    def test_full_overlap(self):
        legacy = [{"npi": "123"}, {"npi": "456"}]
        singleton = [{"npi": "123"}, {"npi": "456"}]
        result = compare_npis(legacy, singleton)
        assert result["overlap_ratio"] == 1.0
        assert result["legacy_only_npis"] == 0

    def test_partial_overlap(self):
        legacy = [{"npi": "123"}, {"npi": "456"}]
        singleton = [{"npi": "123"}, {"npi": "789"}]
        result = compare_npis(legacy, singleton)
        assert result["overlap_ratio"] == 0.5
        assert result["legacy_only_npis"] == 1
        assert result["singleton_only_npis"] == 1


class TestValidateDeduplication:
    def test_no_duplicates(self):
        records = [{"npi": "123"}, {"npi": "456"}, {"npi": "789"}]
        result = validate_deduplication(records)
        assert result["properly_deduplicated"] is True
        assert result["duplicate_npis"] == 0

    def test_has_duplicates(self):
        records = [{"npi": "123"}, {"npi": "123"}, {"npi": "456"}]
        result = validate_deduplication(records)
        assert result["properly_deduplicated"] is False
        assert result["duplicate_npis"] == 1


class TestLoadJsonl:
    def test_load_jsonl_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            jsonl_file = path / "test.jsonl"
            with open(jsonl_file, "wb") as f:
                f.write(orjson.dumps({"npi": "123"}) + b"\n")
                f.write(orjson.dumps({"npi": "456"}) + b"\n")

            records = load_jsonl(path)
            assert len(records) == 2
            assert records[0]["npi"] == "123"

    def test_load_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            records = load_jsonl(Path(tmpdir))
            assert records == []
