"""tools.plan_reader — Architectural drawing parser utilities.

Public API
----------
parse_dimension(text)         Convert an architectural dimension string to metres.
validate_dimensions(ext, ann) Cross-check extracted vs annotated dimensions.
"""

from tools.plan_reader.dimensions import parse_dimension, validate_dimensions

__all__ = ["parse_dimension", "validate_dimensions"]
