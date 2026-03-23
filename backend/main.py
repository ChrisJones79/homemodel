"""
backend/main.py — FastAPI server that exposes backend_to_viewer contract surfaces.

Endpoints
---------
GET /scene/manifest   → SceneManifest
GET /nav/viewpoints   → ViewpointList

Mode is controlled by the HOMEMODEL_MODE environment variable:
  - "stub"  (default) — returns fixture data verbatim from the contract
  - "real"            — queries SchemaStore for live entity data

CORS allowed origins are configured via CORS_ALLOW_ORIGINS (comma-separated,
defaults to "*" for unrestricted LAN access).
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic response models — field names must match the contract exactly.
# ---------------------------------------------------------------------------


class LatLon(BaseModel):
    lat: float
    lon: float


class OriginGPS(BaseModel):
    lat: float
    lon: float
    alt_m: float


class BoundsGPS(BaseModel):
    sw: LatLon
    ne: LatLon


class LodLevel(BaseModel):
    level: int
    max_distance_m: float
    mesh_url: str


class SceneManifest(BaseModel):
    bounds_gps: BoundsGPS
    origin_gps: OriginGPS
    entity_count: int
    lod_levels: list[LodLevel]
    last_updated: str  # ISO 8601 timestamp


class ViewpointGPS(BaseModel):
    lat: float
    lon: float
    alt_m: float


class Viewpoint(BaseModel):
    id: str
    label: str
    position_gps: ViewpointGPS
    look_at_gps: ViewpointGPS
    indoor: bool


class ViewpointList(BaseModel):
    viewpoints: list[Viewpoint]


# ---------------------------------------------------------------------------
# Fixture data — mirrors test_fixtures in contracts/backend_to_viewer.yaml
# ---------------------------------------------------------------------------

_FIXTURE_MANIFEST = SceneManifest(
    bounds_gps=BoundsGPS(
        sw=LatLon(lat=42.98643, lon=-70.98809),
        ne=LatLon(lat=42.98843, lon=-70.98609),
    ),
    origin_gps=OriginGPS(lat=42.98743, lon=-70.98709, alt_m=26.8),
    entity_count=47,
    lod_levels=[
        LodLevel(level=0, max_distance_m=50.0, mesh_url="/scene/tiles/0/0/0.glb"),
        LodLevel(level=1, max_distance_m=200.0, mesh_url="/scene/tiles/1/0/0.glb"),
    ],
    last_updated="2026-03-18T14:00:00Z",
)

_FIXTURE_VIEWPOINTS = ViewpointList(
    viewpoints=[
        Viewpoint(
            id="vp-front-door",
            label="Front Door",
            position_gps=ViewpointGPS(lat=42.98740, lon=-70.98705, alt_m=27.3),
            look_at_gps=ViewpointGPS(lat=42.98740, lon=-70.98700, alt_m=27.3),
            indoor=False,
        )
    ]
)

# ---------------------------------------------------------------------------
# GPS bounds used in real mode (same footprint as fixtures)
# ---------------------------------------------------------------------------

_REAL_BOUNDS = BoundsGPS(
    sw=LatLon(lat=42.98643, lon=-70.98809),
    ne=LatLon(lat=42.98843, lon=-70.98609),
)
_REAL_ORIGIN = OriginGPS(lat=42.98743, lon=-70.98709, alt_m=26.8)
_REAL_LOD_LEVELS = [
    LodLevel(level=0, max_distance_m=50.0, mesh_url="/scene/tiles/0/0/0.glb"),
    LodLevel(level=1, max_distance_m=200.0, mesh_url="/scene/tiles/1/0/0.glb"),
]

# ---------------------------------------------------------------------------
# Stub GLB — minimal valid glTF 2.0 binary containing one triangle mesh.
# Header: magic "glTF" + version 2 + total length (540 bytes).
# JSON chunk: full glTF scene graph (asset, scene, nodes, meshes, accessors,
#             bufferViews, buffers) padded to 4-byte alignment with spaces.
# BIN chunk:  3×VEC3 float32 positions (36 bytes) +
#             3×SCALAR uint16 indices  (6 bytes, padded to 8 bytes).
# ---------------------------------------------------------------------------

_STUB_GLB: bytes = (
    b'glTF\x02\x00\x00\x00\x1c\x02\x00\x00'          # GLB header (12 bytes)
    b'\xd4\x01\x00\x00JSON'                             # JSON chunk header
    b'{"asset":{"version":"2.0"},"scene":0,'
    b'"scenes":[{"nodes":[0]}],'
    b'"nodes":[{"mesh":0}],'
    b'"meshes":[{"primitives":[{"attributes":{"POSITION":0},"indices":1}]}],'
    b'"accessors":['
    b'{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3",'
    b'"min":[0.0,0.0,0.0],"max":[1.0,1.0,0.0]},'
    b'{"bufferView":1,"componentType":5123,"count":3,"type":"SCALAR"}],'
    b'"bufferViews":['
    b'{"buffer":0,"byteOffset":0,"byteLength":36},'
    b'{"buffer":0,"byteOffset":36,"byteLength":6}],'
    b'"buffers":[{"byteLength":44}]}'
    b' '                                                # 1-byte space padding → 4-byte align
    b'\x2c\x00\x00\x00BIN\x00'                         # BIN chunk header (length=44)
    # 3 VEC3 float32 vertices: (0,0,0), (1,0,0), (0,1,0)
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # (0,0,0)
    b'\x00\x00\x80\x3f\x00\x00\x00\x00\x00\x00\x00\x00'  # (1,0,0)
    b'\x00\x00\x00\x00\x00\x00\x80\x3f\x00\x00\x00\x00'  # (0,1,0)
    # 3 uint16 indices: 0,1,2  +  2 zero-bytes padding
    b'\x00\x00\x01\x00\x02\x00\x00\x00'
)

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app(mode: str | None = None) -> FastAPI:
    """Create and return the configured FastAPI application.

    Parameters
    ----------
    mode:
        Override HOMEMODEL_MODE for testing. When *None* (default) the value
        is read from the ``HOMEMODEL_MODE`` environment variable, falling back
        to ``"stub"``. Any value not in ``{"stub", "real"}`` is silently
        treated as ``"stub"``.
    """
    raw_mode: str = (
        mode if mode is not None else os.environ.get("HOMEMODEL_MODE", "stub")
    ).lower()
    resolved_mode: str = raw_mode if raw_mode in {"stub", "real"} else "stub"

    # CORS origins — comma-separated list, defaults to "*" for LAN access.
    cors_env = os.environ.get("CORS_ALLOW_ORIGINS", "*")
    cors_origins = [o.strip() for o in cors_env.split(",")]

    # ------------------------------------------------------------------
    # Lifespan: open SchemaStore once at startup, close on shutdown.
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if resolved_mode == "real":
            from schema.store import SchemaStore  # noqa: PLC0415

            db_path = os.getenv("SCHEMASTORE_DB_PATH", ":memory:")
            store = SchemaStore(db_path=db_path)
            app.state.store = store
            try:
                yield
            finally:
                store.close()
                app.state.store = None
        else:
            app.state.store = None
            yield

    application = FastAPI(
        title="homemodel backend",
        description=(
            "FastAPI server bridging SchemaStore to the 3-D viewer. "
            f"Running in {resolved_mode!r} mode."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Endpoint: GET /scene/manifest
    # ------------------------------------------------------------------

    @application.get(
        "/scene/manifest",
        response_model=SceneManifest,
        summary="SceneManifest — scene bounds, entity count, and LOD table",
    )
    def get_scene_manifest() -> SceneManifest:
        """Return a SceneManifest describing the full scene extent.

        In **stub** mode the fixture values from the contract are returned
        unchanged. In **real** mode the entity count is fetched live from
        SchemaStore; all other fields use the configured GPS bounds.
        """
        if resolved_mode == "stub":
            return _FIXTURE_MANIFEST

        # --- real mode ---
        try:
            store = application.state.store
            bbox = {
                "sw_lat": _REAL_BOUNDS.sw.lat,
                "sw_lon": _REAL_BOUNDS.sw.lon,
                "ne_lat": _REAL_BOUNDS.ne.lat,
                "ne_lon": _REAL_BOUNDS.ne.lon,
            }
            region = store.query_region(bbox)
            live_count: int = region["total_count"]
        except Exception as exc:
            _logger.error("SchemaStore error in /scene/manifest: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="SchemaStore unavailable",
            ) from exc

        return SceneManifest(
            bounds_gps=_REAL_BOUNDS,
            origin_gps=_REAL_ORIGIN,
            entity_count=live_count,
            lod_levels=_REAL_LOD_LEVELS,
            last_updated=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    # ------------------------------------------------------------------
    # Endpoint: GET /nav/viewpoints
    # ------------------------------------------------------------------

    @application.get(
        "/nav/viewpoints",
        response_model=ViewpointList,
        summary="ViewpointList — named camera positions for the viewer nav menu",
    )
    def get_nav_viewpoints() -> ViewpointList:
        """Return a list of named viewpoints for the viewer navigation menu.

        Currently returns the fixture viewpoints in both stub and real mode.
        A future iteration will persist viewpoints in SchemaStore.
        """
        return _FIXTURE_VIEWPOINTS

    # ------------------------------------------------------------------
    # Endpoint: GET /scene/tiles/{z}/{x}/{y}.glb
    # ------------------------------------------------------------------

    @application.get(
        "/scene/tiles/{z}/{x}/{y}.glb",
        summary="SceneTile — terrain mesh tile as glTF binary",
    )
    def get_scene_tile(z: int, x: int, y: int) -> Response:
        """Return a GLB tile for the given tile coordinates.

        In **stub** mode returns a minimal single-triangle GLB regardless of z/x/y.
        In **real** mode returns 501 Not Implemented (tile generation is a future task).
        """
        if resolved_mode == "stub":
            return Response(content=_STUB_GLB, media_type="application/octet-stream")
        raise HTTPException(status_code=501, detail="Tile generation not yet implemented")

    # ------------------------------------------------------------------
    # Endpoint: GET /entities/{entity_id}/mesh
    # ------------------------------------------------------------------

    @application.get(
        "/entities/{entity_id}/mesh",
        summary="EntityMesh — entity detail mesh as glTF binary",
    )
    def get_entity_mesh(entity_id: str) -> Response:
        """Return a GLB mesh for the given entity id.

        In **stub** mode returns a minimal single-triangle GLB regardless of id.
        In **real** mode returns 501 Not Implemented (entity mesh generation is a future task).
        """
        if resolved_mode == "stub":
            return Response(content=_STUB_GLB, media_type="application/octet-stream")
        raise HTTPException(status_code=501, detail="Entity mesh generation not yet implemented")

    return application


# ---------------------------------------------------------------------------
# Module-level app instance (used by uvicorn and pytest TestClient)
# ---------------------------------------------------------------------------

app = create_app()
