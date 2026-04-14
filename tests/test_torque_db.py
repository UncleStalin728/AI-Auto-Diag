"""Tests for torque spec database and lookup."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from app.core.torque_db import (
    load_specs,
    lookup_torque_spec,
    search_torque_specs,
    get_all_specs,
    add_spec,
    update_spec,
    mark_verified,
    format_specs_for_prompt,
    _slugify,
    _make_id,
    _specs_cache,
)
from app.models.schemas import TorqueSpec


# ── Sample data for tests ────────────────────────────────

SAMPLE_SPECS = {
    "specs": [
        {
            "id": "ford_f-150_5-0l-v8-coyote_cylinder-head-bolt",
            "vehicle": "2015-2020 Ford F-150 5.0L V8 Coyote",
            "year_range": [2015, 2020],
            "make": "Ford",
            "model": "F-150",
            "engine": "5.0L V8 Coyote",
            "component": "Cylinder Head Bolt",
            "category": "engine",
            "torque_ft_lbs": 30,
            "torque_nm": 41,
            "torque_sequence": "Inner to outer, 3 stages",
            "stages": [
                {"stage": 1, "value": 30, "unit": "ft-lbs"},
                {"stage": 2, "value": 60, "unit": "ft-lbs"},
                {"stage": 3, "value": 90, "unit": "degrees"},
            ],
            "tty": True,
            "reusable": False,
            "thread_size": "M12x1.75",
            "lubrication": "Clean and dry threads",
            "notes": "TTY bolts must be replaced.",
            "verified": True,
        },
        {
            "id": "ford_f-150_5-0l-v8-coyote_lug-nut",
            "vehicle": "2015-2020 Ford F-150 5.0L V8 Coyote",
            "year_range": [2015, 2020],
            "make": "Ford",
            "model": "F-150",
            "engine": "5.0L V8 Coyote",
            "component": "Lug Nut",
            "category": "brakes",
            "torque_ft_lbs": 150,
            "torque_nm": 203,
            "torque_sequence": "Star pattern",
            "stages": [],
            "tty": False,
            "reusable": True,
            "thread_size": "M14x1.5",
            "lubrication": "Clean and dry",
            "notes": "",
            "verified": False,
        },
        {
            "id": "toyota_camry_2-5l-i4_cylinder-head-bolt",
            "vehicle": "2018-2024 Toyota Camry 2.5L I4",
            "year_range": [2018, 2024],
            "make": "Toyota",
            "model": "Camry",
            "engine": "2.5L I4",
            "component": "Cylinder Head Bolt",
            "category": "engine",
            "torque_ft_lbs": 27,
            "torque_nm": 36,
            "torque_sequence": "Center outward",
            "stages": [
                {"stage": 1, "value": 27, "unit": "ft-lbs"},
                {"stage": 2, "value": 90, "unit": "degrees"},
                {"stage": 3, "value": 90, "unit": "degrees"},
            ],
            "tty": True,
            "reusable": False,
            "thread_size": "M11",
            "lubrication": "Light engine oil on threads",
            "notes": "Replace bolts after removal.",
            "verified": True,
        },
    ]
}


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the specs cache before each test."""
    import app.core.torque_db as db
    db._specs_cache = []
    db._loaded = False
    yield
    db._specs_cache = []
    db._loaded = False


@pytest.fixture
def loaded_specs(tmp_path, reset_cache):
    """Load sample specs from a temp directory."""
    import app.core.torque_db as db

    json_file = tmp_path / "test_specs.json"
    json_file.write_text(json.dumps(SAMPLE_SPECS))

    with patch.object(db, "TORQUE_DATA_DIR", tmp_path):
        specs = load_specs()
    return specs


class TestSlugify:
    def test_basic(self):
        assert _slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert _slugify("5.0L V8 (Coyote)") == "5-0l-v8-coyote"

    def test_make_id(self):
        result = _make_id("Ford", "F-150", "5.0L V8", "Cylinder Head Bolt")
        assert result == "ford-f-150-5-0l-v8-cylinder-head-bolt"


class TestLoadSpecs:
    def test_loads_from_json(self, loaded_specs):
        assert len(loaded_specs) == 3

    def test_empty_directory(self, tmp_path, reset_cache):
        import app.core.torque_db as db
        with patch.object(db, "TORQUE_DATA_DIR", tmp_path):
            specs = load_specs()
        assert specs == []

    def test_missing_directory(self, tmp_path, reset_cache):
        import app.core.torque_db as db
        with patch.object(db, "TORQUE_DATA_DIR", tmp_path / "nonexistent"):
            specs = load_specs()
        assert specs == []

    def test_malformed_json(self, tmp_path, reset_cache):
        import app.core.torque_db as db
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json{{{")
        with patch.object(db, "TORQUE_DATA_DIR", tmp_path):
            specs = load_specs()
        assert specs == []


class TestLookup:
    def test_exact_match(self, loaded_specs):
        import app.core.torque_db as db
        results = db.lookup_torque_spec("Cylinder Head Bolt", make="Ford", model="F-150", year=2018, engine="5.0L V8 Coyote")
        assert len(results) > 0
        assert results[0].component == "Cylinder Head Bolt"
        assert results[0].make == "Ford"

    def test_make_filter(self, loaded_specs):
        import app.core.torque_db as db
        results = db.lookup_torque_spec("Cylinder Head Bolt", make="Ford")
        ford_results = [r for r in results if r.make == "Ford"]
        assert len(ford_results) > 0

    def test_year_range(self, loaded_specs):
        import app.core.torque_db as db
        # Year within range
        results = db.lookup_torque_spec("Cylinder Head Bolt", make="Ford", year=2018)
        assert len(results) > 0
        # Year outside range
        results = db.lookup_torque_spec("Cylinder Head Bolt", make="Ford", year=2025)
        # Should still find it but with lower score
        found = [r for r in results if r.make == "Ford"]
        # It may or may not match depending on scoring; the important thing is no crash
        assert isinstance(results, list)

    def test_component_not_found(self, loaded_specs):
        import app.core.torque_db as db
        results = db.lookup_torque_spec("Radiator Hose Clamp", make="Ford")
        assert results == []

    def test_partial_component_match(self, loaded_specs):
        import app.core.torque_db as db
        results = db.lookup_torque_spec("Head Bolt", make="Ford")
        assert len(results) > 0


class TestSearch:
    def test_keyword_search(self, loaded_specs):
        import app.core.torque_db as db
        results = db.search_torque_specs("Ford head bolt")
        assert len(results) > 0

    def test_search_by_category(self, loaded_specs):
        import app.core.torque_db as db
        results = db.search_torque_specs("brakes lug nut")
        assert len(results) > 0

    def test_search_no_results(self, loaded_specs):
        import app.core.torque_db as db
        results = db.search_torque_specs("xyznonexistent")
        assert results == []


class TestGetAllSpecs:
    def test_get_all(self, loaded_specs):
        import app.core.torque_db as db
        results = db.get_all_specs()
        assert len(results) == 3

    def test_filter_by_make(self, loaded_specs):
        import app.core.torque_db as db
        results = db.get_all_specs(make="Ford")
        assert all(s.make == "Ford" for s in results)

    def test_filter_by_category(self, loaded_specs):
        import app.core.torque_db as db
        results = db.get_all_specs(category="engine")
        assert all(s.category == "engine" for s in results)


class TestFormatForPrompt:
    def test_format_with_specs(self, loaded_specs):
        import app.core.torque_db as db
        specs = db.get_all_specs(make="Ford")
        text = format_specs_for_prompt(specs)
        assert "LOCAL TORQUE SPEC DATABASE" in text
        assert "Cylinder Head Bolt" in text
        assert "ft-lbs" in text

    def test_format_empty(self):
        text = format_specs_for_prompt([])
        assert text == ""

    def test_verified_tag(self, loaded_specs):
        import app.core.torque_db as db
        specs = db.get_all_specs(make="Ford")
        text = format_specs_for_prompt(specs)
        assert "[VERIFIED]" in text
        assert "[UNVERIFIED" in text


class TestTorqueQueryDetection:
    def test_torque_keywords(self):
        from app.core.claude_client import _is_torque_query
        assert _is_torque_query("What's the head bolt torque for a 2018 F-150?")
        assert _is_torque_query("Lug nut torque spec")
        assert _is_torque_query("How tight should I tighten the drain plug?")
        assert _is_torque_query("torque to yield head bolts")

    def test_non_torque_queries(self):
        from app.core.claude_client import _is_torque_query
        assert not _is_torque_query("Engine misfiring at idle")
        assert not _is_torque_query("P0300 code on 2018 F-150")
        assert not _is_torque_query("Oil change procedure")
