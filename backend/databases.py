"""
backend/databases.py — FastAPI router for multi-database discovery and access.

Provides five endpoints:

  GET  /databases                              → DatabaseList
  GET  /databases/{db_name}/entities           → EntityList (optional ?entity_type=)
  GET  /databases/{db_name}/entities/{id}      → Entity dict
  PATCH /databases/{db_name}/entities/{id}     → UpsertResult (properties patch)
  POST  /databases                             → NewDatabaseResult

Database discovery:
  SCHEMASTORE_DB_PATH is interpreted as follows —
    • points to a file  → scan the *parent directory* for *.db files
    • points to a dir   → scan that directory for *.db files
    • unset / empty     → no databases discovered (empty list)

Both stub and real modes are supported, controlled by the *resolved_mode*
argument passed to ``create_databases_router()``.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class DatabaseInfo(BaseModel):
    name: str       # filename stem used as db_name in URL path (e.g. "homemodel")
    filename: str   # full filename on disk (e.g. "homemodel.db")
    size_bytes: int
    entity_count: int


class DatabaseList(BaseModel):
    databases: list[DatabaseInfo]


class EntityPatch(BaseModel):
    properties: dict[str, Any] = {}


class NewDatabaseRequest(BaseModel):
    db_name: str              # target database name (no .db extension, no path separators)
    entity: dict[str, Any]   # full entity dict to insert


class NewDatabaseResult(BaseModel):
    db_name: str
    filename: str
    entity_id: str


# ---------------------------------------------------------------------------
# Fixture data — returned verbatim in stub mode
# ---------------------------------------------------------------------------

_FIXTURE_DATABASES = DatabaseList(
    databases=[
        DatabaseInfo(
            name="homemodel",
            filename="homemodel.db",
            size_bytes=32768,
            entity_count=47,
        ),
        DatabaseInfo(
            name="survey_2026",
            filename="survey_2026.db",
            size_bytes=8192,
            entity_count=12,
        ),
    ]
)

_FIXTURE_ENTITY_LIST: dict[str, Any] = {
    "entities": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "type": "tree",
            "bounds": {"lat": 42.98750, "lon": -70.98720, "alt_m": 28.0},
            "version": 1,
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "type": "tree",
            "bounds": {"lat": 42.98730, "lon": -70.98715, "alt_m": 27.5},
            "version": 1,
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440002",
            "type": "wall",
            "bounds": {"lat": 42.98743, "lon": -70.98709, "alt_m": 26.8},
            "version": 2,
        },
    ],
    "total_count": 3,
}

_FIXTURE_ENTITY: dict[str, Any] = {
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
# Discovery helpers
# ---------------------------------------------------------------------------


def _get_db_dir() -> Path | None:
    """Return the directory to scan for *.db files, or None if unconfigured."""
    raw = os.getenv("SCHEMASTORE_DB_PATH", "").strip()
    if not raw:
        return None
    p = Path(raw)
    if p.is_dir():
        return p
    # It's a file path — use the parent directory.
    parent = p.parent
    return parent if parent.is_dir() else None


def discover_databases() -> list[dict[str, Any]]:
    """Scan the configured database directory for *.db files.

    Returns a list of dicts, each with keys:
    ``name``, ``filename``, ``size_bytes``, ``entity_count``.

    Returns an empty list when SCHEMASTORE_DB_PATH is not set or the path does
    not resolve to a readable directory.
    """
    db_dir = _get_db_dir()
    if db_dir is None:
        return []

    results: list[dict[str, Any]] = []
    for db_file in sorted(db_dir.glob("*.db")):
        entity_count = 0
        try:
            from schema.store import SchemaStore  # noqa: PLC0415

            with SchemaStore(db_path=str(db_file)) as store:
                region = store.query_region(
                    {"sw_lat": -90.0, "sw_lon": -180.0, "ne_lat": 90.0, "ne_lon": 180.0}
                )
                entity_count = region["total_count"]
        except Exception as exc:  # pragma: no cover
            _logger.warning("Could not read entity count from %s: %s", db_file.name, exc)

        results.append(
            {
                "name": db_file.stem,
                "filename": db_file.name,
                "size_bytes": db_file.stat().st_size,
                "entity_count": entity_count,
            }
        )
    return results


def _resolve_db_file(db_name: str) -> Path:
    """Return the Path for a named database, raising HTTPException if not found."""
    # Guard against path traversal.
    if "/" in db_name or "\\" in db_name or db_name.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid database name")

    db_dir = _get_db_dir()
    if db_dir is None:
        raise HTTPException(
            status_code=503,
            detail="SCHEMASTORE_DB_PATH is not configured",
        )
    db_file = db_dir / f"{db_name}.db"
    if not db_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Database not found: {db_name!r}",
        )
    return db_file


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------


def create_databases_router(resolved_mode: str) -> APIRouter:
    """Return an APIRouter for all /databases endpoints.

    Parameters
    ----------
    resolved_mode:
        ``"stub"`` or ``"real"`` — controls whether fixture data or live
        SQLite files are used.
    """
    router = APIRouter(prefix="/databases", tags=["databases"])

    # ------------------------------------------------------------------
    # GET /databases
    # ------------------------------------------------------------------

    @router.get(
        "",
        response_model=DatabaseList,
        summary="DatabaseList — all discovered SQLite databases",
    )
    def get_databases() -> DatabaseList:
        """Return metadata for every *.db file found under SCHEMASTORE_DB_PATH.

        In **stub** mode returns two fixture databases.
        In **real** mode scans the directory derived from SCHEMASTORE_DB_PATH.
        """
        if resolved_mode == "stub":
            return _FIXTURE_DATABASES

        try:
            dbs = discover_databases()
        except Exception as exc:
            _logger.error("Database discovery failed: %s", exc)
            raise HTTPException(
                status_code=503, detail="Database discovery failed"
            ) from exc

        return DatabaseList(databases=[DatabaseInfo(**d) for d in dbs])

    # ------------------------------------------------------------------
    # GET /databases/{db_name}/entities
    # ------------------------------------------------------------------

    @router.get(
        "/{db_name}/entities",
        summary="EntityList — entities in a specific database",
    )
    def get_db_entities(
        db_name: str,
        entity_type: str | None = None,
    ) -> dict[str, Any]:
        """Return all entities in the named database.

        Optionally filter by ``?entity_type=<type>`` to return only entities
        of that type.

        In **stub** mode returns a fixture entity list.
        In **real** mode opens the named *.db file and queries all entities.
        """
        if resolved_mode == "stub":
            entities = list(_FIXTURE_ENTITY_LIST["entities"])
            if entity_type:
                entities = [e for e in entities if e["type"] == entity_type]
            return {"entities": entities, "total_count": len(entities)}

        db_file = _resolve_db_file(db_name)
        try:
            from schema.store import SchemaStore  # noqa: PLC0415

            with SchemaStore(db_path=str(db_file)) as store:
                result: dict[str, Any] = store.query_region(
                    {"sw_lat": -90.0, "sw_lon": -180.0, "ne_lat": 90.0, "ne_lon": 180.0}
                )
        except HTTPException:
            raise
        except Exception as exc:
            _logger.error("Error listing entities in %r: %s", db_name, exc)
            raise HTTPException(status_code=503, detail="Store unavailable") from exc

        if entity_type:
            result["entities"] = [
                e for e in result["entities"] if e["type"] == entity_type
            ]
            result["total_count"] = len(result["entities"])

        return result

    # ------------------------------------------------------------------
    # GET /databases/{db_name}/entities/{entity_id}
    # ------------------------------------------------------------------

    @router.get(
        "/{db_name}/entities/{entity_id}",
        summary="Entity — full entity record from a specific database",
    )
    def get_db_entity(db_name: str, entity_id: str) -> dict[str, Any]:
        """Return the full entity record for *entity_id* from the named database.

        In **stub** mode returns a fixture entity (id field is overridden with
        the requested id so multiple entities appear distinct).
        In **real** mode queries the named *.db file.
        """
        if resolved_mode == "stub":
            return {**_FIXTURE_ENTITY, "id": entity_id}

        db_file = _resolve_db_file(db_name)
        try:
            from schema.store import SchemaStore  # noqa: PLC0415

            with SchemaStore(db_path=str(db_file)) as store:
                return store.get_entity(entity_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            _logger.error(
                "Error getting entity %r from %r: %s", entity_id, db_name, exc
            )
            raise HTTPException(status_code=503, detail="Store unavailable") from exc

    # ------------------------------------------------------------------
    # PATCH /databases/{db_name}/entities/{entity_id}
    # ------------------------------------------------------------------

    @router.patch(
        "/{db_name}/entities/{entity_id}",
        summary="UpsertResult — update properties of an entity in a specific database",
    )
    def patch_db_entity(
        db_name: str,
        entity_id: str,
        patch: EntityPatch,
    ) -> dict[str, Any]:
        """Merge *patch.properties* into the entity and persist the change.

        Only the ``properties`` dict is modified; all other entity fields are
        preserved.  Returns ``{"id", "version", "status"}`` on success.

        In **stub** mode returns a fixture result without touching any files.
        In **real** mode reads the entity, merges properties, and upserts.
        """
        if resolved_mode == "stub":
            return {"id": entity_id, "version": 2, "status": "updated"}

        db_file = _resolve_db_file(db_name)
        try:
            from schema.store import SchemaStore  # noqa: PLC0415

            with SchemaStore(db_path=str(db_file)) as store:
                entity = store.get_entity(entity_id)
                entity["properties"].update(patch.properties)
                return store.upsert_entity(entity)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            _logger.error(
                "Error patching entity %r in %r: %s", entity_id, db_name, exc
            )
            raise HTTPException(status_code=503, detail="Store unavailable") from exc

    # ------------------------------------------------------------------
    # POST /databases
    # ------------------------------------------------------------------

    @router.post(
        "",
        status_code=201,
        response_model=NewDatabaseResult,
        summary="NewDatabaseResult — create a new database with a single entity",
    )
    def create_database(req: NewDatabaseRequest) -> NewDatabaseResult:
        """Create a new *.db file named *req.db_name* and insert *req.entity*.

        The new file is written into the same directory as the existing
        databases (derived from SCHEMASTORE_DB_PATH).  Returns
        ``{db_name, filename, entity_id}`` on success.

        Returns 409 if a database with that name already exists.

        In **stub** mode returns a fixture result without writing any files.
        In **real** mode creates the database file on disk.
        """
        if resolved_mode == "stub":
            return NewDatabaseResult(
                db_name=req.db_name,
                filename=f"{req.db_name}.db",
                entity_id=req.entity.get("id", "stub-entity-id"),
            )

        # Validate name before touching the filesystem.
        if "/" in req.db_name or "\\" in req.db_name or req.db_name.startswith("."):
            raise HTTPException(status_code=400, detail="Invalid database name")

        db_dir = _get_db_dir()
        if db_dir is None:
            raise HTTPException(
                status_code=503,
                detail="SCHEMASTORE_DB_PATH is not configured",
            )

        new_db_file = db_dir / f"{req.db_name}.db"
        if new_db_file.exists():
            raise HTTPException(
                status_code=409,
                detail=f"Database already exists: {req.db_name!r}",
            )

        try:
            from schema.store import SchemaStore  # noqa: PLC0415

            with SchemaStore(db_path=str(new_db_file)) as store:
                result = store.upsert_entity(req.entity)
        except ValueError as exc:
            new_db_file.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            new_db_file.unlink(missing_ok=True)
            _logger.error("Error creating database %r: %s", req.db_name, exc)
            raise HTTPException(status_code=503, detail="Store error") from exc

        return NewDatabaseResult(
            db_name=req.db_name,
            filename=new_db_file.name,
            entity_id=result["id"],
        )

    return router
