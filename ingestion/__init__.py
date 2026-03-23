"""
Ingestion pipeline for submitting measurements, images, and entity batches
into the SchemaStore.

All data passes through validation before being submitted.
"""
from ingestion.pipeline import Ingestion
from ingestion.validate import ValidationResult, validate

__all__ = ["Ingestion", "validate", "ValidationResult"]
