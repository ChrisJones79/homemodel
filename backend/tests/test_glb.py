"""
Tests for backend/main.py — SceneTile and EntityMesh GLB endpoints.

Both endpoints return a minimal single-triangle glTF 2.0 binary (GLB) in stub
mode and 501 Not Implemented in real mode.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def stub_client():
    """TestClient wired to the app in stub mode."""
    from backend.main import create_app  # noqa: PLC0415

    test_app = create_app(mode="stub")
    with TestClient(test_app) as client:
        yield client


@pytest.fixture(scope="module")
def real_client():
    """TestClient wired to the app in real mode (no store seeding needed)."""
    from backend.main import create_app  # noqa: PLC0415

    test_app = create_app(mode="real")
    with TestClient(test_app) as client:
        yield client


# ---------------------------------------------------------------------------
# GET /scene/tiles/{z}/{x}/{y}.glb
# ---------------------------------------------------------------------------


class TestSceneTile:
    """Contract: SceneTile endpoint must return a valid GLB in stub mode."""

    def test_status_200(self, stub_client: TestClient):
        response = stub_client.get("/scene/tiles/0/0/0.glb")
        assert response.status_code == 200, response.text

    def test_content_type(self, stub_client: TestClient):
        response = stub_client.get("/scene/tiles/0/0/0.glb")
        assert response.headers["content-type"] == "application/octet-stream"

    def test_body_nonempty(self, stub_client: TestClient):
        response = stub_client.get("/scene/tiles/0/0/0.glb")
        assert len(response.content) > 0

    def test_glb_magic(self, stub_client: TestClient):
        response = stub_client.get("/scene/tiles/0/0/0.glb")
        assert response.content[:4] == b"glTF"

    def test_real_mode_501(self, real_client: TestClient):
        response = real_client.get("/scene/tiles/0/0/0.glb")
        assert response.status_code == 501


# ---------------------------------------------------------------------------
# GET /entities/{entity_id}/mesh
# ---------------------------------------------------------------------------


class TestEntityMesh:
    """Contract: EntityMesh endpoint must return a valid GLB in stub mode."""

    def test_status_200(self, stub_client: TestClient):
        response = stub_client.get("/entities/some-id/mesh")
        assert response.status_code == 200, response.text

    def test_content_type(self, stub_client: TestClient):
        response = stub_client.get("/entities/some-id/mesh")
        assert response.headers["content-type"] == "application/octet-stream"

    def test_body_nonempty(self, stub_client: TestClient):
        response = stub_client.get("/entities/some-id/mesh")
        assert len(response.content) > 0

    def test_glb_magic(self, stub_client: TestClient):
        response = stub_client.get("/entities/some-id/mesh")
        assert response.content[:4] == b"glTF"

    def test_real_mode_501(self, real_client: TestClient):
        response = real_client.get("/entities/some-id/mesh")
        assert response.status_code == 501
