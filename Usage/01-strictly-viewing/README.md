# Usage 01 — Strictly Viewing

Navigate the 3-D scene and explore the property without inspecting or modifying any entity data.  
This is the lightest interaction mode: only the scene manifest, terrain tiles, and viewpoint list  
are fetched. No entity records, no database writes.

---

## What it does

- Loads a GPS-anchored Three.js scene centred on lat 42.98743, lon -70.98709, alt 26.8 m.
- Streams LOD terrain tile meshes (glTF/GLB) as the camera moves.
- Provides named **viewpoints** (e.g. Front Yard, Back Yard, Roof) reachable via the nav overlay.
- Supports free-movement **walk mode** — WASD / arrow keys to move, right-click drag to look,  
  Q/E for up/down, Shift to sprint.
- Optionally enters a full **WebXR / VR session** (Valve Index or any WebXR-capable headset)  
  via the "Enter VR" button (Chrome/Edge only).

---

## Components involved

| Component | File | Role |
|-----------|------|------|
| Viewer HTML | `viewer/index.html` | Entry point, importmap, UI overlays |
| Scene loader | `viewer/scene.js` | Initialises Three.js, fetches manifest, drives tile loading |
| Tile streamer | `viewer/tiles.js` | LOD tile lifecycle — load, add, remove |
| Viewpoint nav | `viewer/nav.js` | Populates nav buttons, animates camera to viewpoint |
| Walk camera | `viewer/walk.js` | Free-movement WASD camera controller |
| WebXR session | `viewer/xr.js` | VR session lifecycle, XR nav events |
| Debug overlay | `viewer/debug.js` | Bottom-left loading status panel (backtick to toggle) |
| Backend — manifest | `backend/main.py` | `GET /scene/manifest` → `SceneManifest` |
| Backend — viewpoints | `backend/main.py` | `GET /nav/viewpoints` → `ViewpointList` |
| Stub fixtures | `viewer/fixtures/scene_manifest.json` | Used when `?stub=1` (no backend needed) |
| Stub fixtures | `viewer/fixtures/viewpoints.json` | Used when `?stub=1` |

---

## How to invoke

### Option A — via the backend (recommended)

```bash
# Start backend in stub mode (no database required)
HOMEMODEL_MODE=stub uvicorn backend.main:app --port 8000 --reload

# Open in browser
open http://localhost:8000
```

### Option B — stub mode without any backend

```bash
cd viewer
python -m http.server 8080
# open http://localhost:8080/?stub=1
```

Or open `viewer/index.html` as a `file://` URL with `?stub=1` appended.

---

## Controls

| Action | Input |
|--------|-------|
| Move forward/back/left/right | W A S D or arrow keys |
| Look around | Right-click drag |
| Move up / down | Q / E |
| Sprint | Hold Shift |
| Jump to named viewpoint | Click a button in the nav overlay (top-left) |
| Toggle debug overlay | Backtick `` ` `` or click the panel header |
| Enter VR | "Enter VR" button (Chrome/Edge + headset) |

---

## Relevant contracts

- `contracts/backend_to_viewer.yaml` — `SceneManifest`, `SceneTile`, `ViewpointList`
- `contracts/viewer_to_webxr.yaml` — `XRSessionConfig`, `XRSceneHandoff`, `XRNavEvent`
