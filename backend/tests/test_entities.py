"""
Tests for entity endpoints in backend/main.py.

Covers all three entity surfaces from contracts/schema_to_backend.yaml:
  GET  /entities?bbox=sw_lat,sw_lon,ne_lat,ne_lon  → EntityList
  GET  /entities/{id}                               → Entity
  POST /entities                                    → UpsertResult

Stub-mode tests verify fixture data matches the contract.
Real-mode tests seed an in-memory SchemaStore and verify live delegation.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# Fixture entity id from contracts/schema_to_backend.yaml
_FIXTURE_ID = "550e8400-e29b-41d4-a716-446655440000"

# Canonical bounding box that covers the fixture entity location
_BBOX = "42.98700,-70.98750,42.98800,-70.98700"

# Canonical entity payload for POST /entities tests
_ENTITY_PAYLOAD = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "tree",
    "geometry": [[42.98750, -70.98720], [42.98750, -70.98719]],
    "position_gps": {"lat": 42.98750, "lon": -70.98720, "alt_m": 28.0},
    "provenance": {
        "source_type": "manual",
        "source_id": "initial_survey",
        "timestamp": "2026-03-18T12:00:00Z",
        "accuracy_m": 1.0,
    },
    "version": 1,
    "properties": {"species": "white_oak", "dbh_cm": 85, "canopy_radius_m": 8.5},
}


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def stub_client():
    """TestClient wired to the app in stub mode."""
    from backend.main import create_app  # noqa: PLC0415

    test_app = create_app(mode="stub")
    with TestClient(test_app) as client:
        yield client


@pytest.fixture
def real_client():
    """TestClient wired to the app in real mode with a seeded in-memory store."""
    from backend.main import create_app  # noqa: PLC0415

    test_app = create_app(mode="real")
    with TestClient(test_app) as client:
        test_app.state.store.upsert_entity(
            {
                "id": _FIXTURE_ID,
                "type": "tree",
                "geometry": [[42.98750, -70.98720], [42.98750, -70.98719]],
                "position_gps": {"lat": 42.98750, "lon": -70.98720, "alt_m": 28.0},
                "provenance": {
                    "source_type": "manual",
                    "source_id": "initial_survey",
                    "timestamp": "2026-03-18T12:00:00Z",
                    "accuracy_m": 1.0,
                },
            }
        )
        yield client


# ---------------------------------------------------------------------------
# GET /entities?bbox — stub mode
# ---------------------------------------------------------------------------


class TestGetEntitiesStub:
    """EntityList contract: stub mode returns fixture data."""

    def test_status_200(self, stub_client: TestClient):
        response = stub_client.get(f"/entities?bbox={_BBOX}")
        assert response.status_code == 200, response.text

    def test_content_type_json(self, stub_client: TestClient):
        response = stub_client.get(f"/entities?bbox={_BBOX}")
        assert "application/json" in response.headers["content-type"]

    def test_required_fields_present(self, stub_client: TestClient):
        data = stub_client.get(f"/entities?bbox={_BBOX}").json()
        assert {"entities", "total_count"}.issubset(data.keys())

    def test_entities_is_list(self, stub_client: TestClient):
        data = stub_client.get(f"/entities?bbox={_BBOX}").json()
        assert isinstance(data["entities"], list)

    def test_total_count_is_integer(self, stub_client: TestClient):
        data = stub_client.get(f"/entities?bbox={_BBOX}").json()
        assert isinstance(data["total_count"], int)

    def test_entity_summary_shape(self, stub_client: TestClient):
        entities = stub_client.get(f"/entities?bbox={_BBOX}").json()["entities"]
        assert len(entities) > 0
        for ent in entities:
            assert {"id", "type", "bounds", "version"}.issubset(ent.keys())
            assert {"lat", "lon", "alt_m"}.issubset(ent["bounds"].keys())

    def test_fixture_entity_present(self, stub_client: TestClient):
        entities = stub_client.get(f"/entities?bbox={_BBOX}").json()["entities"]
        ids = [e["id"] for e in entities]
        assert _FIXTURE_ID in ids

    def test_missing_bbox_returns_422(self, stub_client: TestClient):
        response = stub_client.get("/entities")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /entities/{id} — stub mode
# ---------------------------------------------------------------------------


class TestGetEntityStub:
    """Entity contract: stub mode returns fixture entity."""

    def test_status_200(self, stub_client: TestClient):
        response = stub_client.get(f"/entities/{_FIXTURE_ID}")
        assert response.status_code == 200, response.text

    def test_content_type_json(self, stub_client: TestClient):
        response = stub_client.get(f"/entities/{_FIXTURE_ID}")
        assert "application/json" in response.headers["content-type"]

    def test_required_fields_present(self, stub_client: TestClient):
        data = stub_client.get(f"/entities/{_FIXTURE_ID}").json()
        required = {"id", "type", "geometry", "position_gps", "provenance", "version", "properties"}
        assert required.issubset(data.keys())

    def test_position_gps_shape(self, stub_client: TestClient):
        pos = stub_client.get(f"/entities/{_FIXTURE_ID}").json()["position_gps"]
        assert {"lat", "lon", "alt_m"}.issubset(pos.keys())

    def test_provenance_shape(self, stub_client: TestClient):
        prov = stub_client.get(f"/entities/{_FIXTURE_ID}").json()["provenance"]
        assert {"source_type", "source_id", "timestamp", "accuracy_m"}.issubset(prov.keys())

    def test_fixture_id(self, stub_client: TestClient):
        data = stub_client.get(f"/entities/{_FIXTURE_ID}").json()
        assert data["id"] == _FIXTURE_ID

    def test_fixture_type(self, stub_client: TestClient):
        data = stub_client.get(f"/entities/{_FIXTURE_ID}").json()
        assert data["type"] == "tree"

    def test_fixture_version(self, stub_client: TestClient):
        data = stub_client.get(f"/entities/{_FIXTURE_ID}").json()
        assert data["version"] == 1

    def test_fixture_position_gps(self, stub_client: TestClient):
        pos = stub_client.get(f"/entities/{_FIXTURE_ID}").json()["position_gps"]
        assert pos["lat"] == pytest.approx(42.98750)
        assert pos["lon"] == pytest.approx(-70.98720)
        assert pos["alt_m"] == pytest.approx(28.0)

    def test_fixture_properties(self, stub_client: TestClient):
        props = stub_client.get(f"/entities/{_FIXTURE_ID}").json()["properties"]
        assert props["species"] == "white_oak"
        assert props["dbh_cm"] == 85
        assert props["canopy_radius_m"] == pytest.approx(8.5)


# ---------------------------------------------------------------------------
# POST /entities — stub mode
# ---------------------------------------------------------------------------


class TestPostEntitiesStub:
    """UpsertResult contract: stub mode returns fixture result."""

    def test_status_201(self, stub_client: TestClient):
        response = stub_client.post("/entities", json=_ENTITY_PAYLOAD)
        assert response.status_code == 201, response.text

    def test_content_type_json(self, stub_client: TestClient):
        response = stub_client.post("/entities", json=_ENTITY_PAYLOAD)
        assert "application/json" in response.headers["content-type"]

    def test_required_fields_present(self, stub_client: TestClient):
        data = stub_client.post("/entities", json=_ENTITY_PAYLOAD).json()
        assert {"id", "version", "status"}.issubset(data.keys())

    def test_fixture_status(self, stub_client: TestClient):
        data = stub_client.post("/entities", json=_ENTITY_PAYLOAD).json()
        assert data["status"] in {"created", "updated"}

    def test_fixture_version_is_integer(self, stub_client: TestClient):
        data = stub_client.post("/entities", json=_ENTITY_PAYLOAD).json()
        assert isinstance(data["version"], int)

    def test_fixture_id(self, stub_client: TestClient):
        data = stub_client.post("/entities", json=_ENTITY_PAYLOAD).json()
        assert data["id"] == _FIXTURE_ID


# ---------------------------------------------------------------------------
# GET /entities?bbox — real mode
# ---------------------------------------------------------------------------


class TestGetEntitiesReal:
    """EntityList: real mode delegates to SchemaStore.query_region."""

    def test_status_200(self, real_client: TestClient):
        response = real_client.get(f"/entities?bbox={_BBOX}")
        assert response.status_code == 200, response.text

    def test_entities_contains_seeded_entity(self, real_client: TestClient):
        data = real_client.get(f"/entities?bbox={_BBOX}").json()
        ids = [e["id"] for e in data["entities"]]
        assert _FIXTURE_ID in ids

    def test_total_count_matches_entities(self, real_client: TestClient):
        data = real_client.get(f"/entities?bbox={_BBOX}").json()
        assert data["total_count"] == len(data["entities"])

    def test_invalid_bbox_returns_422(self, real_client: TestClient):
        response = real_client.get("/entities?bbox=bad,values")
        assert response.status_code == 422

    def test_non_numeric_bbox_returns_422(self, real_client: TestClient):
        response = real_client.get("/entities?bbox=a,b,c,d")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /entities/{id} — real mode
# ---------------------------------------------------------------------------


class TestGetEntityReal:
    """Entity: real mode delegates to SchemaStore.get_entity."""

    def test_status_200(self, real_client: TestClient):
        response = real_client.get(f"/entities/{_FIXTURE_ID}")
        assert response.status_code == 200, response.text

    def test_returns_correct_entity(self, real_client: TestClient):
        data = real_client.get(f"/entities/{_FIXTURE_ID}").json()
        assert data["id"] == _FIXTURE_ID
        assert data["type"] == "tree"

    def test_unknown_id_returns_404(self, real_client: TestClient):
        response = real_client.get("/entities/does-not-exist")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /entities — real mode
# ---------------------------------------------------------------------------


class TestPostEntitiesReal:
    """UpsertResult: real mode delegates to SchemaStore.upsert_entity."""

    def test_create_new_entity_returns_201(self, real_client: TestClient):
        new_entity = {
            **_ENTITY_PAYLOAD,
            "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        }
        response = real_client.post("/entities", json=new_entity)
        assert response.status_code == 201, response.text

    def test_create_returns_created_status(self, real_client: TestClient):
        new_entity = {
            **_ENTITY_PAYLOAD,
            "id": "ffffffff-0000-1111-2222-333333333333",
        }
        data = real_client.post("/entities", json=new_entity).json()
        assert data["status"] == "created"
        assert data["version"] == 1

    def test_update_existing_entity_returns_updated(self, real_client: TestClient):
        # The seeded entity (_FIXTURE_ID) already exists → should be "updated"
        data = real_client.post("/entities", json=_ENTITY_PAYLOAD).json()
        assert data["status"] == "updated"
        assert data["version"] == 2

    def test_upsert_result_has_required_fields(self, real_client: TestClient):
        new_entity = {
            **_ENTITY_PAYLOAD,
            "id": "11111111-2222-3333-4444-555555555555",
        }
        data = real_client.post("/entities", json=new_entity).json()
        assert {"id", "version", "status"}.issubset(data.keys())
