---
name: Structure Builder
description: Models structures, walls, and rooms from measurements and floor plans
---

# Structure Builder Agent

## Goal
A StructureBuilder class that compiles floor plans, laser measurements,
and images into StructureEntity records (structures, walls, rooms),
writing them into SchemaStore via the domains_to_schema contract.

## Contracts
- `contracts/domains_to_schema.yaml` — StructureEntity, BuildRecord
- `contracts/ingestion_to_schema.yaml` — Measurement (laser_p2p, image_derived)

## Process
1. Read the StructureEntity and BuildRecord surfaces in domains_to_schema.yaml
2. Implement StructureBuilder in `structures/builder.py`
3. Implement wall/room extrusion logic in `structures/extrude.py`
4. Write tests in `structures/tests/test_builder.py`
5. Run: `HOMEMODEL_MODE=stub pytest structures/ --tb=short -v`
6. Only open the PR if all tests pass

## Validation
```bash
HOMEMODEL_MODE=stub pytest structures/ --tb=short -v
```

## Present
- pytest output showing all tests green
- A generated StructureEntity with walls and openings matching the contract

## Constraints
- Structures are hierarchical: structure → walls → rooms
- parent_id links walls/rooms to their parent structure
- Openings (doors, windows) are stored on walls with position offsets
- All dimensions in meters
- floor_level: 0=ground, -1=basement, 1=second floor
- Provenance tracks which measurements contributed to each entity
