"""Canopy shape and health-status enumerations for VegetationEntity.

These enumerations enforce the controlled vocabularies specified in
contracts/domains_to_schema.yaml for the VegetationEntity surface.
"""
from __future__ import annotations

from enum import Enum


class CanopyShape(str, Enum):
    """Crown form of an individual tree.

    Values
    ------
    round
        Broadly spherical or dome-shaped crown (e.g. mature oak, maple).
    conical
        Narrow, tapering, Christmas-tree form (e.g. white pine, spruce).
    spreading
        Horizontally wide crown, low height-to-spread ratio (e.g. apple, crab apple).
    columnar
        Tall and narrow, roughly cylindrical (e.g. Lombardy poplar, Italian cypress).
    irregular
        Asymmetric or otherwise non-standard crown (e.g. storm-damaged trees).
    """

    ROUND = "round"
    CONICAL = "conical"
    SPREADING = "spreading"
    COLUMNAR = "columnar"
    IRREGULAR = "irregular"


class HealthStatus(str, Enum):
    """Observed health condition of an individual tree.

    Values
    ------
    healthy
        No visible signs of disease, pest damage, or structural defect.
    stressed
        Reduced foliage, visible dieback, or other early-decline indicators.
    dead
        No live tissue remaining; standing snag or recently fallen.
    unknown
        Condition not assessed or insufficient data (default when omitted).
    """

    HEALTHY = "healthy"
    STRESSED = "stressed"
    DEAD = "dead"
    UNKNOWN = "unknown"
