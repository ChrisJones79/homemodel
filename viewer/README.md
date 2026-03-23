# Viewer

Three.js + WebXR browser viewer for the HomeModel 3D scene. No bundler, no
Node.js — open `index.html` directly in a browser or serve with a static HTTP
server.

---

## Running the Viewer

### Quickest path (stub mode, no backend needed)

```bash
cd viewer
python -m http.server 8080
# open http://localhost:8080?stub=1
```

Stub mode loads all data from `viewer/fixtures/` — no backend required.

### With the live backend

```bash
# Terminal 1 — start the backend
HOMEMODEL_MODE=stub uvicorn backend.main:app --port 8000 --reload

# Terminal 2 — serve the viewer
cd viewer
python -m http.server 8080

# Browser — open http://localhost:8080
```

---

## Stub vs Live Mode

| Trigger | Effect |
|---|---|
| URL param `?stub=1` | Loads fixtures from `viewer/fixtures/` |
| `window.HOMEMODEL_MODE = 'stub'` in console | Same as above |
| No param (default) | Fetches data from `http://localhost:8000` |

Fixture files:

| File | Used for |
|---|---|
| `fixtures/scene_manifest.json` | Scene bounds, origin GPS, LOD levels |
| `fixtures/viewpoints.json` | Navigation menu camera positions |
| `fixtures/entity_tree.json` | Entity inspect panel sample data |

---

## Interacting with the Scene

- **Navigate** — use the navigation menu (populated from viewpoints) to jump to
  named positions.
- **Inspect entities** — click any mesh to open the entity inspect panel.
  The panel shows the entity ID, type, and all property key/value pairs.
- **Close inspect panel** — click the × button or press **Escape**.
- **WebXR** — click the "Enter VR" button (Chrome/Edge on a WebXR device).

---

## Code Layout

```
viewer/
├── index.html          # Entry point; importmap, layout, overlay HTML
├── scene.js            # Three.js scene setup, tile loading, mode detection
├── tiles.js            # Tile manager — fetches /scene/tiles/{z}/{x}/{y}.glb
├── nav.js              # Navigation menu — populated from /nav/viewpoints
├── inspect.js          # Entity pick (Raycaster) + inspect overlay panel
├── xr.js               # WebXR session handoff (Valve Index compatible)
├── vendor/
│   └── three/          # Three.js r160 — vendored locally, no CDN required
└── fixtures/
    ├── scene_manifest.json
    ├── viewpoints.json
    └── entity_tree.json
```

Three.js is imported as bare specifier `'three'`, resolved by the importmap in
`index.html` to the vendored copy in `vendor/three/`.

---

## Scene Coordinates

- **Coordinate system**: Y-up, meters
- **Scene origin**: lat 42.98743, lon -70.98709, alt 26.8 m
- All GPS positions are WGS84; the scene offsets them relative to the origin.

---

## See Also

- Root `README.md` — full setup and add-to-store walkthrough
- `contracts/backend_to_viewer.yaml` — API shapes consumed by the viewer
- `contracts/viewer_to_webxr.yaml` — WebXR session handoff contract
- `backend/README.md` — backend endpoints and modes
