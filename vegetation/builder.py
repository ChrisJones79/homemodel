"""VegetationBuilder — catalogs individual trees as VegetationEntity records.

Implements the ``VegetationBuilder.catalog(survey_data, aerial_images)``
surface defined in contracts/domains_to_schema.yaml.  Every tree is stored as
a first-class entity via ``SchemaStore.upsert_entity()`` and every catalog run
is audited via ``SchemaStore.log_build()``.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from schema.store import SchemaStore
from vegetation.canopy import CanopyShape, HealthStatus

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DOMAIN = "vegetation"
_DEFAULT_HEALTH = HealthStatus.UNKNOWN.value
_VALID_SHAPES: frozenset[str] = frozenset(s.value for s in CanopyShape)
_VALID_HEALTH: frozenset[str] = frozenset(h.value for h in HealthStatus)


# ---------------------------------------------------------------------------
# VegetationBuilder
# ---------------------------------------------------------------------------


class VegetationBuilder:
    """Builds and catalogs VegetationEntity records from survey data.

    Each call to :meth:`catalog` is treated as a single atomic run:

    * Every tree in *survey_data* is converted to a VegetationEntity and
      written to the :class:`~schema.store.SchemaStore` via
      ``upsert_entity()``.
    * A :class:`BuildRecord` is logged via ``log_build()`` regardless of
      whether any errors occurred.

    Parameters
    ----------
    store:
        Opened :class:`~schema.store.SchemaStore` instance to write into.

    Example
    -------
    ::

        with SchemaStore() as store:
            builder = VegetationBuilder(store)
            result = builder.catalog(survey_data)
            print(result["build_record"])
    """

    def __init__(self, store: SchemaStore) -> None:
        self._store = store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def catalog(
        self,
        survey_data: list[dict[str, Any]],
        aerial_images: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Catalog trees from survey data and optional aerial imagery.

        Parameters
        ----------
        survey_data:
            List of tree survey dicts.  Each entry must contain:

            * ``position_gps`` — ``{lat, lon, alt_m}`` trunk-base coordinates.
            * ``properties.height_m`` — estimated total height in metres.
            * ``properties.canopy_radius_m`` — crown radius in metres.
            * ``properties.canopy_shape`` — one of the
              :class:`~vegetation.canopy.CanopyShape` values.

            Optional fields:

            * ``id`` — UUID string; generated if absent.
            * ``properties.species`` — nullable string.
            * ``properties.dbh_cm`` — nullable float.
            * ``properties.health`` — :class:`~vegetation.canopy.HealthStatus`
              value; defaults to ``"unknown"``.
            * ``properties.tags`` — list of freeform label strings.
            * ``source_type`` — provenance source type (default ``"survey"``).
            * ``source_id`` — provenance source identifier.
            * ``accuracy_m`` — GPS accuracy in metres (default ``1.0``).

        aerial_images:
            Optional list of aerial image references.  Reserved for future
            crown-polygon extraction; not consumed in the current
            implementation.

        Returns
        -------
        dict with two keys:

        ``entities``
            List of VegetationEntity dicts that were passed to
            ``upsert_entity()``.
        ``build_record``
            The :class:`BuildRecord` dict that was written to
            ``log_build()``, including ``entities_written``,
            ``entities_updated``, and any ``errors``.
        """
        run_ts = datetime.now(timezone.utc).isoformat()

        entities: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        entities_written = 0
        entities_updated = 0

        # Build source_inputs audit list — prefer entity or source IDs from the
        # raw data so the build record is traceable back to specific inputs.
        source_inputs: list[dict[str, Any]] = [
            {
                "type": "survey_data",
                "id": tree.get("id") or tree.get("source_id") or f"survey_{i}",
                "path": tree.get("source_path", ""),
            }
            for i, tree in enumerate(survey_data)
        ]
        if aerial_images:
            source_inputs += [
                {
                    "type": "aerial_image",
                    "id": (
                        img.get("id") if isinstance(img, dict) else str(img)
                    ) or f"image_{i}",
                    "path": img.get("path", "") if isinstance(img, dict) else "",
                }
                for i, img in enumerate(aerial_images)
            ]

        for i, tree_data in enumerate(survey_data):
            entity_id: str = tree_data.get("id") or str(uuid.uuid4())
            try:
                entity = self._build_entity(entity_id, tree_data, run_ts)
                result = self._store.upsert_entity(entity)
                if result["status"] == "created":
                    entities_written += 1
                else:
                    entities_updated += 1
                entities.append(entity)
            except (ValueError, KeyError, TypeError) as exc:
                errors.append({"entity_id": entity_id, "message": str(exc)})

        build_record: dict[str, Any] = {
            "domain": _DOMAIN,
            "timestamp": run_ts,
            "source_inputs": source_inputs,
            "entities_written": entities_written,
            "entities_updated": entities_updated,
            "errors": errors,
        }
        self._store.log_build(build_record)

        return {"entities": entities, "build_record": build_record}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_entity(
        self,
        entity_id: str,
        tree_data: dict[str, Any],
        timestamp: str,
    ) -> dict[str, Any]:
        """Convert raw survey data into a validated VegetationEntity dict."""
        position_gps: dict[str, float] = tree_data["position_gps"]
        props: dict[str, Any] = tree_data.get("properties", {})

        # --- Required property validation ---
        for required_field in ("height_m", "canopy_radius_m", "canopy_shape"):
            if required_field not in props:
                raise ValueError(f"Missing required property: {required_field!r}")

        canopy_shape: str = props["canopy_shape"]
        if canopy_shape not in _VALID_SHAPES:
            raise ValueError(
                f"Invalid canopy_shape {canopy_shape!r}. "
                f"Must be one of: {sorted(_VALID_SHAPES)}"
            )

        health: str = props.get("health", _DEFAULT_HEALTH)
        if health not in _VALID_HEALTH:
            raise ValueError(
                f"Invalid health {health!r}. "
                f"Must be one of: {sorted(_VALID_HEALTH)}"
            )

        # GeoJSON Point — coordinates are [longitude, latitude] per RFC 7946
        geometry: dict[str, Any] = {
            "type": "Point",
            "coordinates": [position_gps["lon"], position_gps["lat"]],
        }

        provenance: dict[str, Any] = {
            "source_type": tree_data.get("source_type", "survey"),
            "source_id": tree_data.get("source_id", entity_id),
            "timestamp": timestamp,
            "accuracy_m": float(tree_data.get("accuracy_m", 1.0)),
        }

        properties: dict[str, Any] = {
            "species": props.get("species"),
            "dbh_cm": props.get("dbh_cm"),
            "height_m": float(props["height_m"]),
            "canopy_radius_m": float(props["canopy_radius_m"]),
            "canopy_shape": canopy_shape,
            "health": health,
            "tags": list(props.get("tags", [])),
        }

        return {
            "id": entity_id,
            "type": "tree",
            "geometry": geometry,
            "position_gps": position_gps,
            "provenance": provenance,
            "properties": properties,
        }
