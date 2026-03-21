---
name: Vegetation Builder
description: Catalogs trees and vegetation as first-class entities
---

# Vegetation Builder Agent

## Goal
A VegetationBuilder class that creates and manages VegetationEntity
records (individual trees) from survey data and aerial imagery, writing
them into SchemaStore via the domains_to_schema contract.

## Contracts
- `contracts/domains_to_schema.yaml` — VegetationEntity, BuildRecord

## Process
1. Read the VegetationEntity and BuildRecord surfaces in domains_to_schema.yaml
2. Implement VegetationBuilder in `vegetation/builder.py`
3. Implement canopy shape definitions in `vegetation/canopy.py`
4. Write tests in `vegetation/tests/test_builder.py` using the tree_white_pine fixture
5. Run: `HOMEMODEL_MODE=stub pytest vegetation/ --tb=short -v`
6. Only open the PR if all tests pass

## Validation
```bash
HOMEMODEL_MODE=stub pytest vegetation/ --tb=short -v
```

## Present
- pytest output showing all tests green
- A generated VegetationEntity matching the tree_white_pine fixture format

## Constraints
- Individual trees are first-class entities — not grouped or simplified
- Required fields: position_gps, height_m, canopy_radius_m, canopy_shape
- species and dbh_cm are nullable until identified
- canopy_shape enum: round, conical, spreading, columnar, irregular
- health enum: healthy, stressed, dead, unknown
- tags array for freeform labeling (e.g. 'landmark', 'trail_marker')
- Log a BuildRecord for every catalog run
