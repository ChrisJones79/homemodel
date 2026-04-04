"""
Tests for the /databases endpoints added by backend/databases.py.

Covers all five surfaces:
  GET   /databases                              → DatabaseList
  GET   /databases/{db_name}/entities           → EntityList
  GET   /databases/{db_name}/entities/{id}      → Entity dict
  PATCH /databases/{db_name}/entities/{id}      → UpsertResult
  POST  /databases                              → NewDatabaseResult

Both stub-mode (fixture data) and real-mode (temp SQLite files on disk) are
tested.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_DB_NAME = "testdb"
_ENTITY_ID = "550e8400-e29b-41d4-a716-446655440099"

_ENTITY_PAYLOAD = {
    "id": _ENTITY_ID,
    "type": "tree",
    "geometry": [[42.98750, -70.98720], [42.98750, -70.98719]],
    "position_gps": {"lat": 42.98750, "lon": -70.98720, "alt_m": 28.0},
    "provenance": {
        "source_type": "manual",
        "source_id": "test_survey",
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
def real_client(tmp_path, monkeypatch):
    """TestClient in real mode with a temp dir containing a seeded *.db file.

    SCHEMASTORE_DB_PATH is set to the seeded file (not the directory) so that
    main.py can open it as the app-level store while _get_db_dir() in
    databases.py resolves the parent directory for multi-DB discovery.
    """
    db_file = tmp_path / f"{_DB_NAME}.db"
    # Create and seed the database file.
    from schema.store import SchemaStore  # noqa: PLC0415

    with SchemaStore(db_path=str(db_file)) as store:
        store.upsert_entity(_ENTITY_PAYLOAD)

    # Point to the file so main.py opens it as its store and databases.py
    # scans the parent directory for *.db files.
    monkeypatch.setenv("SCHEMASTORE_DB_PATH", str(db_file))

    from backend.main import create_app  # noqa: PLC0415

    test_app = create_app(mode="real")
    with TestClient(test_app) as client:
        yield client


# ---------------------------------------------------------------------------
# GET /databases — stub mode
# ---------------------------------------------------------------------------


class TestGetDatabasesStub:
    def test_status_200(self, stub_client):
        r = stub_client.get("/databases")
        assert r.status_code == 200

    def test_returns_databases_key(self, stub_client):
        data = stub_client.get("/databases").json()
        assert "databases" in data

    def test_fixture_has_two_databases(self, stub_client):
        dbs = stub_client.get("/databases").json()["databases"]
        assert len(dbs) == 2

    def test_database_fields(self, stub_client):
        db = stub_client.get("/databases").json()["databases"][0]
        assert "name" in db
        assert "filename" in db
        assert "size_bytes" in db
        assert "entity_count" in db

    def test_fixture_names(self, stub_client):
        names = {d["name"] for d in stub_client.get("/databases").json()["databases"]}
        assert names == {"homemodel", "survey_2026"}

    def test_entity_count_positive(self, stub_client):
        for db in stub_client.get("/databases").json()["databases"]:
            assert db["entity_count"] >= 0


# ---------------------------------------------------------------------------
# GET /databases/{db_name}/entities — stub mode
# ---------------------------------------------------------------------------


class TestGetDbEntitiesStub:
    def test_status_200(self, stub_client):
        r = stub_client.get("/databases/homemodel/entities")
        assert r.status_code == 200

    def test_returns_entities_key(self, stub_client):
        data = stub_client.get("/databases/homemodel/entities").json()
        assert "entities" in data
        assert "total_count" in data

    def test_fixture_three_entities(self, stub_client):
        data = stub_client.get("/databases/homemodel/entities").json()
        assert data["total_count"] == 3
        assert len(data["entities"]) == 3

    def test_entity_fields(self, stub_client):
        entity = stub_client.get("/databases/homemodel/entities").json()["entities"][0]
        assert "id" in entity
        assert "type" in entity
        assert "bounds" in entity
        assert "version" in entity

    def test_type_filter(self, stub_client):
        data = stub_client.get("/databases/homemodel/entities?entity_type=tree").json()
        assert all(e["type"] == "tree" for e in data["entities"])

    def test_type_filter_returns_subset(self, stub_client):
        data = stub_client.get("/databases/homemodel/entities?entity_type=wall").json()
        assert data["total_count"] == 1


# ---------------------------------------------------------------------------
# GET /databases/{db_name}/entities/{entity_id} — stub mode
# ---------------------------------------------------------------------------


class TestGetDbEntityStub:
    _FIXTURE_FIELDS = {"id", "type", "geometry", "position_gps", "provenance", "version", "properties"}

    def test_status_200(self, stub_client):
        r = stub_client.get("/databases/homemodel/entities/some-id")
        assert r.status_code == 200

    def test_returns_all_fields(self, stub_client):
        data = stub_client.get("/databases/homemodel/entities/some-id").json()
        assert self._FIXTURE_FIELDS.issubset(data.keys())

    def test_id_override(self, stub_client):
        """Stub mode echoes back the requested id."""
        data = stub_client.get("/databases/homemodel/entities/my-custom-id").json()
        assert data["id"] == "my-custom-id"

    def test_properties_present(self, stub_client):
        data = stub_client.get("/databases/homemodel/entities/any").json()
        assert isinstance(data["properties"], dict)


# ---------------------------------------------------------------------------
# PATCH /databases/{db_name}/entities/{entity_id} — stub mode
# ---------------------------------------------------------------------------


class TestPatchDbEntityStub:
    def test_status_200(self, stub_client):
        r = stub_client.patch(
            "/databases/homemodel/entities/some-id",
            json={"properties": {"species": "red_maple"}},
        )
        assert r.status_code == 200

    def test_returns_upsert_shape(self, stub_client):
        r = stub_client.patch(
            "/databases/homemodel/entities/some-id",
            json={"properties": {}},
        )
        data = r.json()
        assert "id" in data
        assert "version" in data
        assert "status" in data

    def test_stub_version_is_2(self, stub_client):
        r = stub_client.patch(
            "/databases/homemodel/entities/some-id",
            json={"properties": {"x": 1}},
        )
        assert r.json()["version"] == 2

    def test_empty_properties_accepted(self, stub_client):
        r = stub_client.patch(
            "/databases/homemodel/entities/some-id",
            json={"properties": {}},
        )
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# POST /databases — stub mode
# ---------------------------------------------------------------------------


class TestPostDatabasesStub:
    def test_status_201(self, stub_client):
        r = stub_client.post(
            "/databases",
            json={"db_name": "new_db", "entity": _ENTITY_PAYLOAD},
        )
        assert r.status_code == 201

    def test_returns_result_shape(self, stub_client):
        r = stub_client.post(
            "/databases",
            json={"db_name": "my_db", "entity": _ENTITY_PAYLOAD},
        )
        data = r.json()
        assert "db_name" in data
        assert "filename" in data
        assert "entity_id" in data

    def test_filename_has_db_extension(self, stub_client):
        r = stub_client.post(
            "/databases",
            json={"db_name": "my_db", "entity": _ENTITY_PAYLOAD},
        )
        assert r.json()["filename"].endswith(".db")

    def test_db_name_echoed(self, stub_client):
        r = stub_client.post(
            "/databases",
            json={"db_name": "echo_db", "entity": _ENTITY_PAYLOAD},
        )
        assert r.json()["db_name"] == "echo_db"


# ---------------------------------------------------------------------------
# GET /databases — real mode
# ---------------------------------------------------------------------------


class TestGetDatabasesReal:
    def test_status_200(self, real_client):
        r = real_client.get("/databases")
        assert r.status_code == 200

    def test_discovers_seeded_db(self, real_client):
        dbs = real_client.get("/databases").json()["databases"]
        names = [d["name"] for d in dbs]
        assert _DB_NAME in names

    def test_entity_count_matches(self, real_client):
        dbs = real_client.get("/databases").json()["databases"]
        db = next(d for d in dbs if d["name"] == _DB_NAME)
        assert db["entity_count"] == 1

    def test_size_bytes_positive(self, real_client):
        dbs = real_client.get("/databases").json()["databases"]
        db = next(d for d in dbs if d["name"] == _DB_NAME)
        assert db["size_bytes"] > 0

    def test_unconfigured_returns_200_empty_list(self, monkeypatch):
        """When SCHEMASTORE_DB_PATH is unset, GET /databases returns 200 with empty list."""
        monkeypatch.delenv("SCHEMASTORE_DB_PATH", raising=False)
        from backend.main import create_app  # noqa: PLC0415

        app = create_app(mode="real")
        with TestClient(app) as client:
            r = client.get("/databases")
        assert r.status_code == 200
        assert r.json()["databases"] == []


# ---------------------------------------------------------------------------
# GET /databases/{db_name}/entities — real mode
# ---------------------------------------------------------------------------


class TestGetDbEntitiesReal:
    def test_status_200(self, real_client):
        r = real_client.get(f"/databases/{_DB_NAME}/entities")
        assert r.status_code == 200

    def test_returns_seeded_entity(self, real_client):
        data = real_client.get(f"/databases/{_DB_NAME}/entities").json()
        assert data["total_count"] == 1
        assert data["entities"][0]["id"] == _ENTITY_ID

    def test_type_filter_matches(self, real_client):
        data = real_client.get(f"/databases/{_DB_NAME}/entities?entity_type=tree").json()
        assert data["total_count"] == 1

    def test_type_filter_no_match(self, real_client):
        data = real_client.get(f"/databases/{_DB_NAME}/entities?entity_type=wall").json()
        assert data["total_count"] == 0

    def test_unknown_db_returns_404(self, real_client):
        r = real_client.get("/databases/nonexistent_db/entities")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /databases/{db_name}/entities/{entity_id} — real mode
# ---------------------------------------------------------------------------


class TestGetDbEntityReal:
    def test_status_200(self, real_client):
        r = real_client.get(f"/databases/{_DB_NAME}/entities/{_ENTITY_ID}")
        assert r.status_code == 200

    def test_entity_id_matches(self, real_client):
        data = real_client.get(f"/databases/{_DB_NAME}/entities/{_ENTITY_ID}").json()
        assert data["id"] == _ENTITY_ID

    def test_entity_properties(self, real_client):
        data = real_client.get(f"/databases/{_DB_NAME}/entities/{_ENTITY_ID}").json()
        assert data["properties"]["species"] == "white_oak"

    def test_unknown_entity_returns_404(self, real_client):
        r = real_client.get(f"/databases/{_DB_NAME}/entities/no-such-id")
        assert r.status_code == 404

    def test_unknown_db_returns_404(self, real_client):
        r = real_client.get(f"/databases/nodb/entities/{_ENTITY_ID}")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /databases/{db_name}/entities/{entity_id} — real mode
# ---------------------------------------------------------------------------


class TestPatchDbEntityReal:
    def test_status_200(self, real_client):
        r = real_client.patch(
            f"/databases/{_DB_NAME}/entities/{_ENTITY_ID}",
            json={"properties": {"species": "red_maple"}},
        )
        assert r.status_code == 200

    def test_version_incremented(self, real_client):
        r = real_client.patch(
            f"/databases/{_DB_NAME}/entities/{_ENTITY_ID}",
            json={"properties": {"dbh_cm": 90}},
        )
        assert r.json()["version"] >= 2

    def test_property_persisted(self, real_client):
        real_client.patch(
            f"/databases/{_DB_NAME}/entities/{_ENTITY_ID}",
            json={"properties": {"canopy_radius_m": 10.0}},
        )
        data = real_client.get(
            f"/databases/{_DB_NAME}/entities/{_ENTITY_ID}"
        ).json()
        assert data["properties"]["canopy_radius_m"] == 10.0

    def test_unknown_entity_returns_404(self, real_client):
        r = real_client.patch(
            f"/databases/{_DB_NAME}/entities/no-such-id",
            json={"properties": {}},
        )
        assert r.status_code == 404

    def test_unknown_db_returns_404(self, real_client):
        r = real_client.patch(
            f"/databases/nodb/entities/{_ENTITY_ID}",
            json={"properties": {}},
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /databases — real mode
# ---------------------------------------------------------------------------


class TestPostDatabasesReal:
    def test_status_201(self, tmp_path, monkeypatch):
        db_file = tmp_path / f"{_DB_NAME}.db"
        from schema.store import SchemaStore  # noqa: PLC0415

        with SchemaStore(db_path=str(db_file)) as s:
            s.upsert_entity(_ENTITY_PAYLOAD)
        monkeypatch.setenv("SCHEMASTORE_DB_PATH", str(db_file))
        from backend.main import create_app  # noqa: PLC0415

        test_app = create_app(mode="real")
        with TestClient(test_app) as client:
            r = client.post(
                "/databases",
                json={"db_name": "brand_new", "entity": _ENTITY_PAYLOAD},
            )
        assert r.status_code == 201

    def test_creates_db_file(self, tmp_path, monkeypatch):
        db_file = tmp_path / f"{_DB_NAME}.db"
        from schema.store import SchemaStore  # noqa: PLC0415

        with SchemaStore(db_path=str(db_file)) as s:
            s.upsert_entity(_ENTITY_PAYLOAD)
        monkeypatch.setenv("SCHEMASTORE_DB_PATH", str(db_file))
        from backend.main import create_app  # noqa: PLC0415

        test_app = create_app(mode="real")
        with TestClient(test_app) as client:
            client.post(
                "/databases",
                json={"db_name": "file_check_db", "entity": _ENTITY_PAYLOAD},
            )
        assert (tmp_path / "file_check_db.db").exists()

    def test_entity_readable_after_create(self, tmp_path, monkeypatch):
        db_file = tmp_path / f"{_DB_NAME}.db"
        from schema.store import SchemaStore  # noqa: PLC0415

        with SchemaStore(db_path=str(db_file)) as s:
            s.upsert_entity(_ENTITY_PAYLOAD)
        monkeypatch.setenv("SCHEMASTORE_DB_PATH", str(db_file))
        from backend.main import create_app  # noqa: PLC0415

        test_app = create_app(mode="real")
        with TestClient(test_app) as client:
            client.post(
                "/databases",
                json={"db_name": "readable_db", "entity": _ENTITY_PAYLOAD},
            )
            data = client.get(
                f"/databases/readable_db/entities/{_ENTITY_ID}"
            ).json()
        assert data["id"] == _ENTITY_ID

    def test_duplicate_db_returns_409(self, tmp_path, monkeypatch):
        db_file = tmp_path / f"{_DB_NAME}.db"
        from schema.store import SchemaStore  # noqa: PLC0415

        with SchemaStore(db_path=str(db_file)) as s:
            s.upsert_entity(_ENTITY_PAYLOAD)
        monkeypatch.setenv("SCHEMASTORE_DB_PATH", str(db_file))
        from backend.main import create_app  # noqa: PLC0415

        test_app = create_app(mode="real")
        payload = {"db_name": "dup_db", "entity": _ENTITY_PAYLOAD}
        with TestClient(test_app) as client:
            client.post("/databases", json=payload)
            r = client.post("/databases", json=payload)
        assert r.status_code == 409

    def test_invalid_db_name_returns_400(self, real_client):
        r = real_client.post(
            "/databases",
            json={"db_name": "../evil", "entity": _ENTITY_PAYLOAD},
        )
        assert r.status_code == 400
