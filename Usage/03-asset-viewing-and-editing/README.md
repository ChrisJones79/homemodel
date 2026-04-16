# Usage 03 — Asset Viewing and Editing

Open the **📂 Asset Browser** overlay to browse every database on disk, list the entities inside  
each one, view an isolated 3-D preview of any entity, and edit its properties — then save or  
discard changes.  You can also create a brand-new database from the browser.

This is the only usage mode that combines **viewing** and **writing** within the viewer itself.

---

## What it does

The Asset Browser is a full-screen three-column overlay:

| Column | Content | Backing API |
|--------|---------|-------------|
| **Left** | Discovered database list | `GET /databases` |
| **Middle** | Entity list for the selected database | `GET /databases/{name}/entities` (optionally filtered by `?entity_type=`) |
| **Right** | Isolated 3-D mesh preview + attribute key=value editor | `GET /databases/{name}/entities/{id}` |

### Editing workflow

1. Select a database → entity list populates.
2. Click an entity → the right panel loads its 3-D preview and lists all `properties` as editable fields.
3. Edit one or more property values in the fields.  Changes are **local** until saved.
4. **Save** → `PATCH /databases/{name}/entities/{id}` sends only the changed `properties`.
5. **Revert** → reloads the entity from the API, discarding all pending edits.

### Additional actions

- **View in Place** — teleports the main scene camera to the entity's `position_gps` coordinates  
  and closes the browser overlay, so you can see the entity in its real-world context.
- **Save as New DB…** — prompts for a new database name and calls `POST /databases` with the  
  current entity as its first record.  Useful for branching a copy of an entity into a new dataset.
- **Toggle theme** — switches the isolated preview between dark and light backgrounds.

---

## Components involved

| Component | File | Role |
|-----------|------|------|
| Asset Browser module | `viewer/browser.js` | All three-column logic, edit state, API calls |
| Viewer HTML | `viewer/index.html` | `#browser-overlay` panel, "📂 Asset Browser" nav button |
| Backend — list DBs | `backend/databases.py` | `GET /databases` → `DatabaseList` |
| Backend — list entities | `backend/databases.py` | `GET /databases/{name}/entities` → `EntityList` |
| Backend — get entity | `backend/databases.py` | `GET /databases/{name}/entities/{id}` → `Entity` |
| Backend — patch entity | `backend/databases.py` | `PATCH /databases/{name}/entities/{id}` → `UpsertResult` |
| Backend — new database | `backend/databases.py` | `POST /databases` → `NewDatabaseResult` |
| SchemaStore | `schema/store.py` | `get_entity()`, `upsert_entity()` |

---

## How to invoke

```bash
# Real mode required for edits to persist
HOMEMODEL_MODE=real \
  SCHEMASTORE_DB_PATH=/path/to/homemodel.db \
  uvicorn backend.main:app --port 8000 --reload

open http://localhost:8000
```

1. Click the **📂 Asset Browser** button in the nav overlay (top-left).
2. Select a database from the left column.
3. Select an entity from the middle column.
4. Edit properties in the right column.
5. Click **Save** to persist, **Revert** to discard, or **View in Place** to jump to it in the scene.

> **Note:** In stub mode (`HOMEMODEL_MODE=stub`) the `PATCH` and `POST /databases` endpoints  
> acknowledge the request but do **not** write to disk.  Use real mode for persistent edits.

---

## Relevant contracts

- `contracts/backend_to_viewer.yaml` — `DatabaseList`, `DatabaseInfo`, `EntityList`, `Entity`, `UpsertResult`
- `contracts/schema_to_backend.yaml` — `Entity` shape
