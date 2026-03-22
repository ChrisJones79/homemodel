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
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    domain           TEXT NOT NULL,
    timestamp        TEXT NOT NULL,
    source_inputs    TEXT NOT NULL DEFAULT '[]',   -- JSON array
    entities_written INTEGER NOT NULL DEFAULT 0,
    entities_updated INTEGER NOT NULL DEFAULT 0,
    errors           TEXT NOT NULL DEFAULT '[]'    -- JSON array
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
            ORDER  BY version ASC
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
    # Surface 5 — log_build  (BuildRecord, domains_to_schema contract)
    # ------------------------------------------------------------------

    def log_build(self, build_record: dict) -> dict[str, Any]:
        """Persist a domain build record.

        Parameters
        ----------
        build_record:
            Dict matching the BuildRecord contract fields::

                {
                    "domain":            str,   # "terrain" | "structures" | "vegetation"
                    "timestamp":         str,   # ISO-8601
                    "source_inputs":     list,  # [{type, id, path}, ...]
                    "entities_written":  int,
                    "entities_updated":  int,
                    "errors":            list,  # [{entity_id, message}, ...]
                }

        Returns
        -------
        The stored record dict with an additional ``"id"`` key (auto-increment
        integer assigned by the database).
        """
        required = ("domain", "timestamp", "entities_written", "entities_updated")
        missing = [f for f in required if f not in build_record]
        if missing:
            raise ValueError(f"BuildRecord is missing required fields: {missing}")

        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO build_records
                    (domain, timestamp, source_inputs,
                     entities_written, entities_updated, errors)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    build_record["domain"],
                    build_record["timestamp"],
                    json.dumps(build_record.get("source_inputs", [])),
                    build_record["entities_written"],
                    build_record["entities_updated"],
                    json.dumps(build_record.get("errors", [])),
                ),
            )
        return {**build_record, "id": cursor.lastrowid}

    def get_build_records(
        self,
        domain: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return all stored build records, optionally filtered by domain.

        Parameters
        ----------
        domain:
            When provided only records for that domain are returned.

        Returns
        -------
        List of build record dicts ordered by ``id`` ascending.
        """
        if domain is not None:
            rows = self._conn.execute(
                "SELECT * FROM build_records WHERE domain = ? ORDER BY id ASC",
                (domain,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM build_records ORDER BY id ASC"
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
    # Convenience
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._conn.close()

    def __enter__(self) -> "SchemaStore":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
