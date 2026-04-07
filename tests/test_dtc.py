"""Tests for DTC database and lookup."""

import pytest
from app.core.dtc_database import lookup_dtc, get_all_codes


class TestDTCLookup:
    """Test DTC code lookup functionality."""

    def test_known_code_p0300(self):
        """P0300 should return misfire data."""
        result = lookup_dtc("P0300")
        assert result is not None
        assert result.code == "P0300"
        assert "misfire" in result.description.lower()
        assert result.category == "powertrain"
        assert result.severity == "critical"
        assert len(result.common_causes) > 0
        assert len(result.diagnostic_steps) > 0

    def test_known_code_p0171(self):
        """P0171 should return lean condition data."""
        result = lookup_dtc("P0171")
        assert result is not None
        assert "lean" in result.description.lower()
        assert result.category == "powertrain"

    def test_known_code_p0420(self):
        """P0420 should return catalyst efficiency data."""
        result = lookup_dtc("P0420")
        assert result is not None
        assert "catalyst" in result.description.lower()

    def test_case_insensitive(self):
        """Lookup should be case-insensitive."""
        upper = lookup_dtc("P0300")
        lower = lookup_dtc("p0300")
        assert upper is not None
        assert lower is not None
        assert upper.code == lower.code

    def test_unknown_powertrain_code(self):
        """Unknown P-codes should return categorized info."""
        result = lookup_dtc("P0999")
        assert result is not None
        assert result.category == "powertrain"
        assert result.severity == "informational"

    def test_unknown_chassis_code(self):
        """Unknown C-codes should be categorized as chassis."""
        result = lookup_dtc("C0100")
        assert result is not None
        assert result.category == "chassis"

    def test_unknown_body_code(self):
        """Unknown B-codes should be categorized as body."""
        result = lookup_dtc("B0100")
        assert result is not None
        assert result.category == "body"

    def test_unknown_network_code(self):
        """Unknown U-codes should be categorized as network."""
        result = lookup_dtc("U0100")
        assert result is not None
        assert result.category == "network"

    def test_invalid_code(self):
        """Completely invalid codes should return None."""
        result = lookup_dtc("X")
        assert result is None

    def test_get_all_codes(self):
        """Should return a sorted list of known codes."""
        codes = get_all_codes()
        assert len(codes) > 0
        assert codes == sorted(codes)
        assert "P0300" in codes

    def test_whitespace_handling(self):
        """Codes with whitespace should still resolve."""
        result = lookup_dtc("  P0300  ")
        assert result is not None
        assert result.code == "P0300"
