# Usage 02 — Asset Viewing

Click any visible mesh in the 3-D scene to open the **Inspect panel** — a read-only overlay that  
shows the clicked entity's id, type, and full properties as returned by the backend.  
No data is modified. The panel is dismissed with **Escape** or the × button.

---

## What it does

- Casts a ray from the camera through the click point (Three.js `Raycaster`).
- Reads `mesh.userData.entityId` from the first intersected mesh.
- Fetches the entity record for that id from the backend (or a local stub fixture).
- Renders the entity's `id`, `type`, and `properties` in the `#inspect-panel` overlay.
- In **stub mode** each pre-placed stub mesh has its own fixture file so clicking different  
  objects always shows different data without a live backend.

---

## Components involved

| Component | File | Role |
|-----------|------|------|
| Inspect module | `viewer/inspect.js` | Raycaster, panel renderer, fixture/live fetch |
| Scene | `viewer/scene.js` | Wires `initInspect()` during scene init |
| Backend — single entity | `backend/main.py` | `GET /entities/{id}` → `Entity` |
| Backend — region query | `backend/main.py` | `GET /entities?bbox=…` → `EntityList` |
| SchemaStore | `schema/store.py` | `get_entity(id)` |
| Stub fixtures | `viewer/fixtures/entity_tree.json` | Tree entity fixture (stub mode) |
| Stub fixtures | `viewer/fixtures/entity_house.json` | House entity fixture (stub mode) |

---

## How to invoke

```bash
# Start backend (stub or real mode)
HOMEMODEL_MODE=stub uvicorn backend.main:app --port 8000 --reload

# Open viewer
open http://localhost:8000
```

**Click any visible mesh** in the scene.  The inspect panel slides in from the right showing  
the entity data.  Press **Escape** or click **×** to close it.

In stub mode (`?stub=1`) the scene pre-places a visible tree mesh and house mesh — click either  
to see the associated fixture data without a live backend.

---

## Relevant contracts

- `contracts/backend_to_viewer.yaml` — `Entity`, `EntityList`
- `contracts/schema_to_backend.yaml` — `Entity` shape returned by `SchemaStore.get_entity()`
