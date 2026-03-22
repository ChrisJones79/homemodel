"""
Tests for backend/main.py — SceneManifest and ViewpointList endpoints.

All tests run in stub mode, which returns fixture data matching the
contracts/backend_to_viewer.yaml test_fixtures section.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def stub_client():
    """TestClient wired to the app in stub mode."""
    os.environ["HOMEMODEL_MODE"] = "stub"

    # Import *after* setting the env-var so create_app() picks up "stub".
    from backend.main import create_app  # noqa: PLC0415

    test_app = create_app(mode="stub")
    with TestClient(test_app) as client:
        yield client


# ---------------------------------------------------------------------------
# GET /scene/manifest
# ---------------------------------------------------------------------------


class TestSceneManifest:
    """Contract: SceneManifest fields must be present and correct."""

    def test_status_200(self, stub_client: TestClient):
        response = stub_client.get("/scene/manifest")
        assert response.status_code == 200, response.text

    def test_content_type_json(self, stub_client: TestClient):
        response = stub_client.get("/scene/manifest")
        assert "application/json" in response.headers["content-type"]

    def test_required_fields_present(self, stub_client: TestClient):
        data = stub_client.get("/scene/manifest").json()
        required = {"bounds_gps", "origin_gps", "entity_count", "lod_levels", "last_updated"}
        missing = required - data.keys()
        assert not missing, f"Response missing fields: {missing}"

    def test_bounds_gps_shape(self, stub_client: TestClient):
        bounds = stub_client.get("/scene/manifest").json()["bounds_gps"]
        assert "sw" in bounds and "ne" in bounds
        for corner in ("sw", "ne"):
            assert "lat" in bounds[corner]
            assert "lon" in bounds[corner]

    def test_origin_gps_shape(self, stub_client: TestClient):
        origin = stub_client.get("/scene/manifest").json()["origin_gps"]
        assert {"lat", "lon", "alt_m"}.issubset(origin.keys())

    def test_lod_levels_shape(self, stub_client: TestClient):
        lod_levels = stub_client.get("/scene/manifest").json()["lod_levels"]
        assert isinstance(lod_levels, list)
        assert len(lod_levels) > 0
        for entry in lod_levels:
            assert {"level", "max_distance_m", "mesh_url"}.issubset(entry.keys())

    def test_entity_count_is_integer(self, stub_client: TestClient):
        entity_count = stub_client.get("/scene/manifest").json()["entity_count"]
        assert isinstance(entity_count, int)

    def test_last_updated_is_string(self, stub_client: TestClient):
        last_updated = stub_client.get("/scene/manifest").json()["last_updated"]
        assert isinstance(last_updated, str) and len(last_updated) > 0

    # -- fixture value assertions ------------------------------------------

    def test_fixture_entity_count(self, stub_client: TestClient):
        data = stub_client.get("/scene/manifest").json()
        assert data["entity_count"] == 47

    def test_fixture_bounds_sw(self, stub_client: TestClient):
        sw = stub_client.get("/scene/manifest").json()["bounds_gps"]["sw"]
        assert sw["lat"] == pytest.approx(42.98643)
        assert sw["lon"] == pytest.approx(-70.98809)

    def test_fixture_bounds_ne(self, stub_client: TestClient):
        ne = stub_client.get("/scene/manifest").json()["bounds_gps"]["ne"]
        assert ne["lat"] == pytest.approx(42.98843)
        assert ne["lon"] == pytest.approx(-70.98609)

    def test_fixture_origin_gps(self, stub_client: TestClient):
        origin = stub_client.get("/scene/manifest").json()["origin_gps"]
        assert origin["lat"] == pytest.approx(42.98743)
        assert origin["lon"] == pytest.approx(-70.98709)
        assert origin["alt_m"] == pytest.approx(26.8)

    def test_fixture_lod_levels_count(self, stub_client: TestClient):
        lod_levels = stub_client.get("/scene/manifest").json()["lod_levels"]
        assert len(lod_levels) == 2

    def test_fixture_lod_level_0(self, stub_client: TestClient):
        lod = stub_client.get("/scene/manifest").json()["lod_levels"][0]
        assert lod["level"] == 0
        assert lod["max_distance_m"] == pytest.approx(50.0)
        assert lod["mesh_url"] == "/scene/tiles/0/0/0.glb"

    def test_fixture_lod_level_1(self, stub_client: TestClient):
        lod = stub_client.get("/scene/manifest").json()["lod_levels"][1]
        assert lod["level"] == 1
        assert lod["max_distance_m"] == pytest.approx(200.0)
        assert lod["mesh_url"] == "/scene/tiles/1/0/0.glb"

    def test_fixture_last_updated(self, stub_client: TestClient):
        last_updated = stub_client.get("/scene/manifest").json()["last_updated"]
        assert last_updated == "2026-03-18T14:00:00Z"


# ---------------------------------------------------------------------------
# GET /nav/viewpoints
# ---------------------------------------------------------------------------


class TestNavViewpoints:
    """Contract: ViewpointList must contain at least the fixture viewpoint."""

    def test_status_200(self, stub_client: TestClient):
        response = stub_client.get("/nav/viewpoints")
        assert response.status_code == 200, response.text

    def test_viewpoints_key_present(self, stub_client: TestClient):
        data = stub_client.get("/nav/viewpoints").json()
        assert "viewpoints" in data

    def test_viewpoints_is_list(self, stub_client: TestClient):
        viewpoints = stub_client.get("/nav/viewpoints").json()["viewpoints"]
        assert isinstance(viewpoints, list)

    def test_viewpoint_shape(self, stub_client: TestClient):
        viewpoints = stub_client.get("/nav/viewpoints").json()["viewpoints"]
        assert len(viewpoints) > 0
        for vp in viewpoints:
            assert {"id", "label", "position_gps", "look_at_gps", "indoor"}.issubset(
                vp.keys()
            )
            for gps_field in ("position_gps", "look_at_gps"):
                assert {"lat", "lon", "alt_m"}.issubset(vp[gps_field].keys())
            assert isinstance(vp["indoor"], bool)

    def test_fixture_front_door_viewpoint(self, stub_client: TestClient):
        viewpoints = stub_client.get("/nav/viewpoints").json()["viewpoints"]
        front_door = next((vp for vp in viewpoints if vp["id"] == "vp-front-door"), None)
        assert front_door is not None, "Expected viewpoint 'vp-front-door' not found"
        assert front_door["label"] == "Front Door"
        assert front_door["indoor"] is False
        assert front_door["position_gps"]["lat"] == pytest.approx(42.98740)
        assert front_door["position_gps"]["lon"] == pytest.approx(-70.98705)
        assert front_door["position_gps"]["alt_m"] == pytest.approx(27.3)


# ---------------------------------------------------------------------------
# CORS headers
# ---------------------------------------------------------------------------


class TestCORS:
    """CORS must be enabled for all origins (LAN viewer access)."""

    def test_cors_preflight_allowed(self, stub_client: TestClient):
        response = stub_client.options(
            "/scene/manifest",
            headers={"Origin": "http://192.168.1.100:3000", "Access-Control-Request-Method": "GET"},
        )
        # FastAPI with allow_origins=["*"] returns 200 for OPTIONS preflight.
        assert response.status_code == 200

    def test_cors_header_present_on_get(self, stub_client: TestClient):
        response = stub_client.get(
            "/scene/manifest", headers={"Origin": "http://192.168.1.100:3000"}
        )
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "*"
