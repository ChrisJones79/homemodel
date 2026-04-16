# Usage

This directory documents every distinct way a person or system can interact with **HomeModel**.  
Each subfolder is self-contained: it describes what the interaction does, which components are involved,  
how to invoke it, and what the expected result looks like.

No source code lives here.  Nothing in `Usage/` affects the runtime behaviour of any module.  
The core folders (`backend/`, `viewer/`, `schema/`, `ingestion/`, `terrain/`, `structures/`,  
`vegetation/`, `tools/`, `contracts/`, `scripts/`, `planning/`) are unchanged.

---

## Subfolders

| # | Folder | What it covers |
|---|--------|----------------|
| 1 | [`01-strictly-viewing/`](./01-strictly-viewing/README.md) | Free-movement 3-D navigation of the scene — terrain tiles, named viewpoints, and WebXR/VR immersion. No entity data or database required. |
| 2 | [`02-asset-viewing/`](./02-asset-viewing/README.md) | Clicking a mesh in the live 3-D scene to open the read-only **Inspect** panel, which shows the entity's id, type, and properties fetched from the backend. |
| 3 | [`03-asset-viewing-and-editing/`](./03-asset-viewing-and-editing/README.md) | The **Asset Browser** overlay — browse databases, list entities, open an isolated 3-D preview, and save property edits or create a new database. |
| 4 | [`04-asset-creation/`](./04-asset-creation/README.md) | Creating a new entity record via the REST API (`POST /entities`) or bootstrapping a brand-new database with an initial entity (`POST /databases`). |
| 5 | [`05-data-ingestion/`](./05-data-ingestion/README.md) | All pipeline-driven ways to get data into the database — measurements, images, bulk import, domain builders, map/parcel ingestion, and the plan-reader pipeline. |

---

## How these usage types relate to each other

```
┌─────────────────────────────────────────────────────────────┐
│                         HomeModel                           │
│                                                             │
│  Viewer (browser)          Backend (FastAPI)   Database     │
│  ─────────────────         ────────────────   ─────────     │
│  01 Strictly Viewing  ───► GET /scene/manifest              │
│                            GET /nav/viewpoints              │
│                                                             │
│  02 Asset Viewing     ───► GET /entities/{id}  ◄── schema/  │
│                                                             │
│  03 Asset Browser     ───► GET  /databases/…   ◄── schema/  │
│                            PATCH /databases/…  ──► schema/  │
│                            POST  /databases    ──► schema/  │
│                                                             │
│  04 Asset Creation    ───► POST /entities      ──► schema/  │
│                                                             │
│  05 Data Ingestion         (various paths)     ──► schema/  │
└─────────────────────────────────────────────────────────────┘
```

Usage types 01–02 are **read-only**.  
Usage type 03 is **read + write** (edit existing, create new DB).  
Usage types 04–05 are **write** (add data to the database).
