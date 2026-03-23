"""
Ingestion pipeline for submitting measurements, images, and entity batches
into the SchemaStore.

All submissions are validated before being sent to the store.
In stub mode, SchemaStore calls are mocked but pipeline logic executes.
"""
from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock

from ingestion.validate import validate


class Ingestion:
    """Ingestion pipeline that validates and submits data to SchemaStore.

    Parameters
    ----------
    schema_store : SchemaStore or Mock
        The schema store instance to submit data to.
        In stub mode (HOMEMODEL_MODE=stub), this should be a mock.
    """

    def __init__(self, schema_store: Any = None) -> None:
        self._store = schema_store
        self._stub_mode = os.environ.get("HOMEMODEL_MODE") == "stub"

        # In stub mode, use a mock store if none provided
        if self._stub_mode and self._store is None:
            self._store = MagicMock()

    def submit_measurement(self, measurement: dict) -> dict[str, Any]:
        """Submit a measurement to the SchemaStore.

        Validates the measurement before submission.
        Converts the measurement into an Entity and calls SchemaStore.upsert_entity().

        Parameters
        ----------
        measurement : dict
            Measurement payload matching the Measurement contract

        Returns
        -------
        dict
            UpsertResult from SchemaStore: {"id": str, "version": int, "status": str}

        Raises
        ------
        ValueError
            If validation fails
        """
        # Validate first
        validation = validate(measurement, "measurement")
        if not validation.valid:
            error_msgs = [f"{e['field']}: {e['message']}" for e in validation.errors]
            raise ValueError(f"Measurement validation failed: {'; '.join(error_msgs)}")

        # Convert measurement to entity format for SchemaStore
        entity = self._measurement_to_entity(measurement)

        # Submit to SchemaStore
        if self._stub_mode:
            # In stub mode, return a mock result
            return {
                "id": entity["id"],
                "version": 1,
                "status": "created"
            }
        else:
            return self._store.upsert_entity(entity)

    def submit_image(self, image: dict) -> dict[str, Any]:
        """Submit an image record to the SchemaStore.

        Validates the image record before submission.
        Calls SchemaStore.attach_image().

        Parameters
        ----------
        image : dict
            ImageRecord payload matching the ImageRecord contract

        Returns
        -------
        dict
            Result from SchemaStore with image_id and status

        Raises
        ------
        ValueError
            If validation fails
        """
        # Validate first
        validation = validate(image, "image")
        if not validation.valid:
            error_msgs = [f"{e['field']}: {e['message']}" for e in validation.errors]
            raise ValueError(f"Image validation failed: {'; '.join(error_msgs)}")

        # Submit to SchemaStore
        if self._stub_mode:
            # In stub mode, return a mock result
            return {
                "image_id": "00000000-0000-0000-0000-000000000000",
                "status": "attached",
                "file_path": image["file_path"]
            }
        else:
            # Determine entity_id - use first linked entity or None
            entity_id = None
            if image.get("linked_entity_ids") and len(image["linked_entity_ids"]) > 0:
                entity_id = image["linked_entity_ids"][0]

            # Call attach_image
            image_id = self._store.attach_image(entity_id, image)
            return {
                "image_id": image_id,
                "status": "attached",
                "file_path": image["file_path"]
            }

    def submit_bulk(self, batch: dict) -> dict[str, Any]:
        """Submit a batch of entities to the SchemaStore.

        Validates the batch before submission.
        Calls SchemaStore.bulk_upsert() with the specified conflict strategy.

        Parameters
        ----------
        batch : dict
            EntityBatch payload matching the EntityBatch contract

        Returns
        -------
        dict
            Result from SchemaStore with counts of created/updated/skipped entities

        Raises
        ------
        ValueError
            If validation fails
        """
        # Validate first
        validation = validate(batch, "batch")
        if not validation.valid:
            error_msgs = [f"{e['field']}: {e['message']}" for e in validation.errors]
            raise ValueError(f"Batch validation failed: {'; '.join(error_msgs)}")

        # Submit to SchemaStore
        if self._stub_mode:
            # In stub mode, return a mock result
            entity_count = len(batch["entities"])
            return {
                "source": batch["source"],
                "total": entity_count,
                "created": entity_count,
                "updated": 0,
                "skipped": 0,
                "errors": []
            }
        else:
            # Call bulk_upsert
            return self._store.bulk_upsert(batch)

    def validate(self, payload: Any, payload_type: str = "measurement") -> dict[str, Any]:
        """Validate a payload without submitting it.

        This is exposed for testing and debugging purposes.

        Parameters
        ----------
        payload : dict
            The payload to validate
        payload_type : str
            Type of payload: 'measurement', 'image', or 'batch'

        Returns
        -------
        dict
            ValidationResult: {"valid": bool, "errors": list, "warnings": list}
        """
        validation = validate(payload, payload_type)
        return validation.to_dict()

    def _measurement_to_entity(self, measurement: dict) -> dict[str, Any]:
        """Convert a Measurement payload to an Entity dict for SchemaStore.

        Parameters
        ----------
        measurement : dict
            Measurement payload

        Returns
        -------
        dict
            Entity dict matching the schema Entity contract
        """
        import uuid

        # Generate or use provided entity_id
        entity_id = measurement.get("entity_id")
        if entity_id is None:
            entity_id = str(uuid.uuid4())

        # Build position_gps from reference_points if available, otherwise use zero point
        position_gps = {"lat": 0.0, "lon": 0.0, "alt_m": 0.0}
        if "reference_points" in measurement and measurement["reference_points"]:
            # Use the first reference point as the entity position
            first_point = measurement["reference_points"][0]["position_gps"]
            position_gps = {
                "lat": first_point["lat"],
                "lon": first_point["lon"],
                "alt_m": first_point["alt_m"]
            }

        # Build entity geometry from reference_points
        geometry = []
        if "reference_points" in measurement:
            for point in measurement["reference_points"]:
                gps = point["position_gps"]
                geometry.append([gps["lat"], gps["lon"]])

        # If no geometry, create a simple point geometry
        if not geometry:
            geometry = [[position_gps["lat"], position_gps["lon"]]]

        # Build entity properties from measurement data
        properties = {
            "measurement_type": measurement["measurement_type"],
            "value": measurement["value"],
            "unit": measurement["unit"]
        }
        if "reference_points" in measurement:
            properties["reference_points"] = measurement["reference_points"]

        return {
            "id": entity_id,
            "type": f"measurement_{measurement['measurement_type']}",
            "geometry": geometry,
            "position_gps": position_gps,
            "provenance": measurement["provenance"],
            "properties": properties
        }
