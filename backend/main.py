"""
backend/main.py — FastAPI server that exposes backend_to_viewer contract surfaces.

Endpoints
---------
GET /scene/manifest   → SceneManifest
GET /nav/viewpoints   → ViewpointList

Mode is controlled by the HOMEMODEL_MODE environment variable:
  - "stub"  (default) — returns fixture data verbatim from the contract
  - "real"            — queries SchemaStore for live entity data

CORS is enabled for all origins so the LAN viewer can reach the server.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Allow the repo root to be imported when the module is executed directly.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

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
# Application factory
# ---------------------------------------------------------------------------


def create_app(mode: str | None = None) -> FastAPI:
    """Create and return the configured FastAPI application.

    Parameters
    ----------
    mode:
        Override HOMEMODEL_MODE for testing. When *None* (default) the value
        is read from the ``HOMEMODEL_MODE`` environment variable, falling back
        to ``"stub"``.
    """
    resolved_mode: str = (
        mode if mode is not None else os.environ.get("HOMEMODEL_MODE", "stub")
    ).lower()

    application = FastAPI(
        title="homemodel backend",
        description=(
            "FastAPI server bridging SchemaStore to the 3-D viewer. "
            f"Running in {resolved_mode!r} mode."
        ),
        version="0.1.0",
    )

    # CORS — allow all origins so the LAN viewer (any IP) can reach the API.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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
            from schema.store import SchemaStore  # noqa: PLC0415

            store = SchemaStore()
            bbox = {
                "sw_lat": _REAL_BOUNDS.sw.lat,
                "sw_lon": _REAL_BOUNDS.sw.lon,
                "ne_lat": _REAL_BOUNDS.ne.lat,
                "ne_lon": _REAL_BOUNDS.ne.lon,
            }
            region = store.query_region(bbox)
            live_count: int = region["total_count"]
        except Exception as exc:  # pragma: no cover
            raise HTTPException(
                status_code=503,
                detail=f"SchemaStore unavailable: {exc}",
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

    return application


# ---------------------------------------------------------------------------
# Module-level app instance (used by uvicorn and pytest TestClient)
# ---------------------------------------------------------------------------

app = create_app()
