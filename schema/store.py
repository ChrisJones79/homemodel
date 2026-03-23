"""
SchemaStore — SQLite-backed implementation of all four surfaces defined in
contracts/schema_to_backend.yaml:

  • get_entity(id)          → Entity dict
  • query_region(bbox)      → EntityList dict
  • upsert_entity(entity)   → UpsertResult dict
  • get_history(id)         → EntityHistory dict
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_CREATE_ENTITIES = """
CREATE TABLE IF NOT EXISTS entities (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    geometry    TEXT NOT NULL,           -- JSON text
    gps_lat     REAL NOT NULL,
    gps_lon     REAL NOT NULL,
    gps_alt_m   REAL NOT NULL,
    provenance  TEXT NOT NULL,           -- JSON text
    version     INTEGER NOT NULL DEFAULT 1,
    properties  TEXT NOT NULL DEFAULT '{}'  -- JSON text
);
"""

_CREATE_HISTORY = """
CREATE TABLE IF NOT EXISTS entity_history (
    rowid       INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id   TEXT NOT NULL,
    version     INTEGER NOT NULL,
    timestamp   TEXT NOT NULL,          -- ISO-8601 from provenance
    provenance  TEXT NOT NULL,          -- JSON snapshot
    geometry    TEXT NOT NULL,          -- JSON snapshot
    properties  TEXT NOT NULL,          -- JSON snapshot
    diff_summary TEXT NOT NULL DEFAULT ''
);
"""

_CREATE_BUILD_RECORDS = """
CREATE TABLE IF NOT EXISTS build_records (
    id               TEXT PRIMARY KEY,
    domain           TEXT NOT NULL,
    timestamp        TEXT NOT NULL,     -- ISO-8601
    source_inputs    TEXT NOT NULL,     -- JSON array
    entities_written INTEGER NOT NULL DEFAULT 0,
    entities_updated INTEGER NOT NULL DEFAULT 0,
    errors           TEXT NOT NULL DEFAULT '[]'  -- JSON array
);
"""

_CREATE_IMAGES = """
CREATE TABLE IF NOT EXISTS images (
    id               TEXT PRIMARY KEY,
    entity_id        TEXT,
    file_path        TEXT NOT NULL,
    format           TEXT NOT NULL,
    size_bytes       INTEGER NOT NULL,
    capture_gps      TEXT NOT NULL,     -- JSON text
    capture_heading  TEXT,               -- JSON text, nullable
    capture_timestamp TEXT NOT NULL,
    source_type      TEXT NOT NULL,
    linked_entity_ids TEXT NOT NULL DEFAULT '[]',  -- JSON array
    FOREIGN KEY (entity_id) REFERENCES entities(id)
);
"""


class SchemaStore:
    """SQLite-backed entity store.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file, or ``:memory:`` for an
        in-process ephemeral database (default).
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._create_tables()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _create_tables(self) -> None:
        with self._conn:
            self._conn.execute(_CREATE_ENTITIES)
            self._conn.execute(_CREATE_HISTORY)
            self._conn.execute(_CREATE_BUILD_RECORDS)
            self._conn.execute(_CREATE_IMAGES)

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "type": row["type"],
            "geometry": json.loads(row["geometry"]),
            "position_gps": {
                "lat": row["gps_lat"],
                "lon": row["gps_lon"],
                "alt_m": row["gps_alt_m"],
            },
            "provenance": json.loads(row["provenance"]),
            "version": row["version"],
            "properties": json.loads(row["properties"]),
        }

    @staticmethod
    def _validate_entity(entity: dict) -> None:
        """Raise ValueError for obviously malformed entities."""
        required = ("id", "type", "geometry", "position_gps", "provenance")
        missing = [f for f in required if f not in entity]
        if missing:
            raise ValueError(f"Entity is missing required fields: {missing}")

        gps = entity["position_gps"]
        if not isinstance(gps, dict) or not {"lat", "lon", "alt_m"}.issubset(gps):
            raise ValueError(
                "position_gps must be a dict with keys lat, lon, alt_m"
            )

        prov = entity["provenance"]
        if not isinstance(prov, dict):
            raise ValueError("provenance must be a dict")

    # ------------------------------------------------------------------
    # Surface 1 — get_entity
    # ------------------------------------------------------------------

    def get_entity(self, id: str) -> dict[str, Any]:
        """Return the current entity dict for *id*.

        Raises
        ------
        KeyError
            If no entity with the given id exists.
        """
        row = self._conn.execute(
            "SELECT * FROM entities WHERE id = ?", (id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Entity not found: {id!r}")
        return self._row_to_dict(row)

    # ------------------------------------------------------------------
    # Surface 2 — query_region
    # ------------------------------------------------------------------

    def query_region(self, bbox: dict[str, float]) -> dict[str, Any]:
        """Return all entities whose GPS position falls within *bbox*.

        Parameters
        ----------
        bbox:
            ``{sw_lat, sw_lon, ne_lat, ne_lon}``

        Returns
        -------
        EntityList dict::

            {
                "entities": [{"id", "type", "bounds", "version"}, ...],
                "total_count": int,
            }
        """
        required_keys = {"sw_lat", "sw_lon", "ne_lat", "ne_lon"}
        missing = required_keys - bbox.keys()
        if missing:
            raise ValueError(f"bbox is missing keys: {missing}")

        rows = self._conn.execute(
            """
            SELECT id, type, gps_lat, gps_lon, gps_alt_m, version
            FROM   entities
            WHERE  gps_lat BETWEEN :sw_lat AND :ne_lat
              AND  gps_lon BETWEEN :sw_lon AND :ne_lon
            """,
            {
                "sw_lat": bbox["sw_lat"],
                "ne_lat": bbox["ne_lat"],
                "sw_lon": bbox["sw_lon"],
                "ne_lon": bbox["ne_lon"],
            },
        ).fetchall()

        entities = [
            {
                "id": r["id"],
                "type": r["type"],
                "bounds": {
                    "lat": r["gps_lat"],
                    "lon": r["gps_lon"],
                    "alt_m": r["gps_alt_m"],
                },
                "version": r["version"],
            }
            for r in rows
        ]
        return {"entities": entities, "total_count": len(entities)}

    # ------------------------------------------------------------------
    # Surface 3 — upsert_entity
    # ------------------------------------------------------------------

    def upsert_entity(self, entity: dict) -> dict[str, Any]:
        """Insert or update an entity.

        * On **create**: version is set to 1 (any supplied value is ignored).
        * On **update**: version is incremented by 1.
        * A provenance snapshot is always written to ``entity_history``.

        Returns
        -------
        UpsertResult::

            {"id": str, "version": int, "status": "created" | "updated"}
        """
        self._validate_entity(entity)

        entity_id: str = entity["id"]
        gps: dict = entity["position_gps"]
        provenance_str = json.dumps(entity["provenance"])
        geometry_str = json.dumps(entity["geometry"])
        properties_str = json.dumps(entity.get("properties", {}))
        timestamp: str = entity["provenance"].get("timestamp", "")

        existing = self._conn.execute(
            "SELECT version FROM entities WHERE id = ?", (entity_id,)
        ).fetchone()

        if existing is None:
            # --- INSERT ---
            new_version = 1
            diff_summary = "initial_insert"
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO entities
                        (id, type, geometry, gps_lat, gps_lon, gps_alt_m,
                         provenance, version, properties)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity_id,
                        entity["type"],
                        geometry_str,
                        gps["lat"],
                        gps["lon"],
                        gps["alt_m"],
                        provenance_str,
                        new_version,
                        properties_str,
                    ),
                )
                self._conn.execute(
                    """
                    INSERT INTO entity_history
                        (entity_id, version, timestamp, provenance,
                         geometry, properties, diff_summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity_id,
                        new_version,
                        timestamp,
                        provenance_str,
                        geometry_str,
                        properties_str,
                        diff_summary,
                    ),
                )
            status = "created"
        else:
            # --- UPDATE ---
            new_version = existing["version"] + 1
            diff_summary = f"version_bump:{existing['version']}->{new_version}"
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE entities
                    SET    type       = ?,
                           geometry   = ?,
                           gps_lat    = ?,
                           gps_lon    = ?,
                           gps_alt_m  = ?,
                           provenance = ?,
                           version    = ?,
                           properties = ?
                    WHERE  id = ?
                    """,
                    (
                        entity["type"],
                        geometry_str,
                        gps["lat"],
                        gps["lon"],
                        gps["alt_m"],
                        provenance_str,
                        new_version,
                        properties_str,
                        entity_id,
                    ),
                )
                self._conn.execute(
                    """
                    INSERT INTO entity_history
                        (entity_id, version, timestamp, provenance,
                         geometry, properties, diff_summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity_id,
                        new_version,
                        timestamp,
                        provenance_str,
                        geometry_str,
                        properties_str,
                        diff_summary,
                    ),
                )
            status = "updated"

        return {"id": entity_id, "version": new_version, "status": status}

    # ------------------------------------------------------------------
    # Surface 4 — get_history
    # ------------------------------------------------------------------

    def get_history(self, id: str) -> dict[str, Any]:
        """Return all recorded revisions for entity *id*.

        Raises
        ------
        KeyError
            If no entity with the given id exists.
        """
        # Confirm entity exists
        exists = self._conn.execute(
            "SELECT 1 FROM entities WHERE id = ?", (id,)
        ).fetchone()
        if exists is None:
            raise KeyError(f"Entity not found: {id!r}")

        rows = self._conn.execute(
            """
            SELECT version, timestamp, provenance, diff_summary
            FROM   entity_history
            WHERE  entity_id = ?
            ORDER  BY version DESC
            """,
            (id,),
        ).fetchall()

        revisions = [
            {
                "version": r["version"],
                "timestamp": r["timestamp"],
                "provenance": json.loads(r["provenance"]),
                "diff_summary": r["diff_summary"],
            }
            for r in rows
        ]
        return {"id": id, "revisions": revisions}

    # ------------------------------------------------------------------
    # Surface 5 — log_build  (BuildRecord)
    # ------------------------------------------------------------------

    def log_build(self, record: dict) -> dict[str, Any]:
        """Persist a BuildRecord produced by a domain builder.

        Parameters
        ----------
        record:
            Dict with keys: id, domain, timestamp, source_inputs,
            entities_written, entities_updated, errors.

        Returns
        -------
        ``{"id": str, "status": "logged"}``
        """
        required = ("id", "domain", "timestamp")
        missing = [f for f in required if f not in record]
        if missing:
            raise ValueError(f"BuildRecord is missing required fields: {missing}")

        record_id: str = record["id"]
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO build_records
                    (id, domain, timestamp, source_inputs,
                     entities_written, entities_updated, errors)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    record["domain"],
                    record["timestamp"],
                    json.dumps(record.get("source_inputs", [])),
                    int(record.get("entities_written", 0)),
                    int(record.get("entities_updated", 0)),
                    json.dumps(record.get("errors", [])),
                ),
            )
        return {"id": record_id, "status": "logged"}

    def get_build_records(self, domain: str | None = None) -> list[dict[str, Any]]:
        """Return all logged BuildRecords, optionally filtered by *domain*."""
        if domain is not None:
            rows = self._conn.execute(
                "SELECT * FROM build_records WHERE domain = ? ORDER BY timestamp DESC",
                (domain,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM build_records ORDER BY timestamp DESC"
            ).fetchall()

        return [
            {
                "id": r["id"],
                "domain": r["domain"],
                "timestamp": r["timestamp"],
                "source_inputs": json.loads(r["source_inputs"]),
                "entities_written": r["entities_written"],
                "entities_updated": r["entities_updated"],
                "errors": json.loads(r["errors"]),
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Surface 6 — attach_image
    # ------------------------------------------------------------------

    def attach_image(self, entity_id: str | None, image_record: dict) -> str:
        """Attach an image record to an entity (or standalone).

        Parameters
        ----------
        entity_id:
            UUID of the entity to link the image to, or None for standalone images
        image_record:
            ImageRecord dict matching the ingestion_to_schema contract

        Returns
        -------
        str
            The image_id (generated UUID)

        Raises
        ------
        ValueError
            If the image_record is missing required fields
        KeyError
            If entity_id is provided but doesn't exist
        """
        import uuid

        # Validate required fields
        required = ("file_path", "format", "size_bytes", "capture_gps",
                    "capture_timestamp", "source_type")
        missing = [f for f in required if f not in image_record]
        if missing:
            raise ValueError(f"ImageRecord is missing required fields: {missing}")

        # Validate entity exists if provided
        if entity_id is not None:
            exists = self._conn.execute(
                "SELECT 1 FROM entities WHERE id = ?", (entity_id,)
            ).fetchone()
            if exists is None:
                raise KeyError(f"Entity not found: {entity_id!r}")

        # Generate image ID
        image_id = str(uuid.uuid4())

        # Serialize JSON fields
        capture_gps_str = json.dumps(image_record["capture_gps"])
        capture_heading = image_record.get("capture_heading")
        capture_heading_str = json.dumps(capture_heading) if capture_heading else None
        linked_entity_ids_str = json.dumps(image_record.get("linked_entity_ids", []))

        # Insert image record
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO images
                    (id, entity_id, file_path, format, size_bytes,
                     capture_gps, capture_heading, capture_timestamp,
                     source_type, linked_entity_ids)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    image_id,
                    entity_id,
                    image_record["file_path"],
                    image_record["format"],
                    image_record["size_bytes"],
                    capture_gps_str,
                    capture_heading_str,
                    image_record["capture_timestamp"],
                    image_record["source_type"],
                    linked_entity_ids_str,
                ),
            )

        return image_id

    # ------------------------------------------------------------------
    # Surface 7 — bulk_upsert
    # ------------------------------------------------------------------

    def bulk_upsert(self, batch: dict) -> dict[str, Any]:
        """Bulk upsert entities with configurable conflict strategy.

        Parameters
        ----------
        batch:
            EntityBatch dict with:
            - source: str
            - entities: list of Entity dicts
            - conflict_strategy: "skip" | "overwrite" | "version_bump"

        Returns
        -------
        dict
            {
                "source": str,
                "total": int,
                "created": int,
                "updated": int,
                "skipped": int,
                "errors": [{"id": str, "message": str}, ...]
            }

        Raises
        ------
        ValueError
            If batch is missing required fields or has invalid conflict_strategy
        """
        # Validate batch structure
        required = ("source", "entities", "conflict_strategy")
        missing = [f for f in required if f not in batch]
        if missing:
            raise ValueError(f"EntityBatch is missing required fields: {missing}")

        conflict_strategy = batch["conflict_strategy"]
        valid_strategies = ("skip", "overwrite", "version_bump")
        if conflict_strategy not in valid_strategies:
            raise ValueError(
                f"Invalid conflict_strategy: {conflict_strategy!r}. "
                f"Must be one of: {valid_strategies}"
            )

        entities = batch["entities"]
        results = {
            "source": batch["source"],
            "total": len(entities),
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": []
        }

        for entity in entities:
            try:
                self._validate_entity(entity)
                entity_id = entity["id"]

                # Check if entity exists
                existing = self._conn.execute(
                    "SELECT version FROM entities WHERE id = ?", (entity_id,)
                ).fetchone()

                if existing is None:
                    # Entity doesn't exist - always create
                    self.upsert_entity(entity)
                    results["created"] += 1
                else:
                    # Entity exists - apply conflict strategy
                    if conflict_strategy == "skip":
                        # Skip existing entities
                        results["skipped"] += 1
                    elif conflict_strategy == "overwrite":
                        # Overwrite existing entity (increments version)
                        self.upsert_entity(entity)
                        results["updated"] += 1
                    elif conflict_strategy == "version_bump":
                        # Increment version and keep history
                        self.upsert_entity(entity)
                        results["updated"] += 1

            except Exception as e:
                results["errors"].append({
                    "id": entity.get("id", "unknown"),
                    "message": str(e)
                })

        return results

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._conn.close()

    def __enter__(self) -> "SchemaStore":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
