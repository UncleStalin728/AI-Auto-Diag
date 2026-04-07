"""Tests for the diagnostic API endpoint (unit tests without Claude API calls)."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.routes.diagnose import _parse_diagnosis


client = TestClient(app)


class TestAppRoutes:
    """Test basic app routing."""

    def test_root(self):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "AI Auto Diag"
        assert data["status"] == "running"

    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_dtc_lookup_known_code(self):
        resp = client.get("/api/dtc/P0300")
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["info"]["code"] == "P0300"

    def test_dtc_lookup_unknown_code(self):
        resp = client.get("/api/dtc/P9999")
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is False

    def test_dtc_list(self):
        resp = client.get("/api/dtc")
        assert resp.status_code == 200
        codes = resp.json()
        assert isinstance(codes, list)
        assert "P0300" in codes


class TestDiagnosisParsing:
    """Test the response parser without requiring Claude API."""

    def test_parse_basic_response(self):
        text = """**Analysis**
        The P0300 code indicates random misfires.

        **Most Likely Causes**
        - Worn spark plugs
        - Faulty ignition coil
        - Vacuum leak

        **Diagnostic Steps**
        - Check spark plugs
        - Swap ignition coils
        - Smoke test intake

        **Related DTCs**
        - P0301
        - P0302
        """
        result = _parse_diagnosis(text, ["manual.pdf"])
        assert result.diagnosis == text
        assert len(result.sources) == 1
        assert "manual.pdf" in result.sources

    def test_parse_high_confidence(self):
        text = "The code most likely indicates a worn catalytic converter."
        result = _parse_diagnosis(text, [])
        assert result.confidence == "high"

    def test_parse_low_confidence(self):
        text = "This could be several things and might be hard to determine."
        result = _parse_diagnosis(text, [])
        assert result.confidence == "low"

    def test_parse_medium_confidence(self):
        text = "The symptoms suggest checking the following components."
        result = _parse_diagnosis(text, [])
        assert result.confidence == "medium"
