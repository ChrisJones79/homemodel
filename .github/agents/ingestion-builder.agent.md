---
name: Ingestion Builder
description: Data ingestion pipeline for measurements, images, and bulk imports
---

# Ingestion Builder Agent

## Goal
An Ingestion pipeline that validates and submits measurements, images,
and bulk entity batches into SchemaStore via the ingestion_to_schema
contract.

## Contracts
- `contracts/ingestion_to_schema.yaml` — Measurement, ImageRecord, EntityBatch, ValidationResult

## Process
1. Read the ingestion_to_schema.yaml contract before writing any code
2. Implement Ingestion class in `ingestion/pipeline.py`
3. Implement validation logic in `ingestion/validate.py`
4. Write tests in `ingestion/tests/test_pipeline.py` using laser_measurement and drone_image fixtures
5. Run: `HOMEMODEL_MODE=stub pytest ingestion/ --tb=short -v`
6. Only open the PR if all tests pass

## Validation
```bash
HOMEMODEL_MODE=stub pytest ingestion/ --tb=short -v
```

## Present
- pytest output showing all tests green
- Demonstration of validation catching bad input (missing fields, invalid enums)

## Constraints
- Validation runs before every submit — no unvalidated data enters SchemaStore
- Measurement types: laser_p2p, gps_point, image_derived, drone_telemetry
- Image source types: phone, drone_aerial, drone_ground, dslr, scan
- Bulk import requires a conflict_strategy: skip, overwrite, or version_bump
- Provenance is mandatory on all measurements
- In stub mode, SchemaStore calls are mocked — pipeline logic still executes
