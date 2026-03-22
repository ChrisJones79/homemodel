"""
Entity dataclass and related type definitions for the SchemaStore.

All fields mirror the contract in contracts/schema_to_backend.yaml.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Provenance:
    source_type: str
    source_id: str
    timestamp: str
    accuracy_m: float


@dataclass
class PositionGPS:
    lat: float
    lon: float
    alt_m: float


@dataclass
class Entity:
    """A single versioned entity stored in the SchemaStore.

    Fields
    ------
    id          UUID string
    type        Enum: terrain_patch | structure | wall | room | tree | feature
    geometry    GeoJSON object or vertex list (serialised as JSON in SQLite)
    position_gps  {lat, lon, alt_m} — stored as 3 REAL columns
    provenance  {source_type, source_id, timestamp, accuracy_m}
    version     Auto-incremented integer; starts at 1 on first insert
    properties  Free-form type-specific key/values
    """

    id: str
    type: str
    geometry: Any                           # list or dict
    position_gps: dict[str, float]          # {lat, lon, alt_m}
    provenance: dict[str, Any]              # {source_type, source_id, timestamp, accuracy_m}
    version: int = 1
    properties: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "geometry": self.geometry,
            "position_gps": self.position_gps,
            "provenance": self.provenance,
            "version": self.version,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Entity":
        return cls(
            id=data["id"],
            type=data["type"],
            geometry=data["geometry"],
            position_gps=data["position_gps"],
            provenance=data["provenance"],
            version=data.get("version", 1),
            properties=data.get("properties", {}),
        )
