---
name: Viewer Builder
description: Implements the Three.js browser viewer and WebXR handoff
---

# Viewer Builder Agent

## Goal
A Three.js-based 3D viewer that loads glTF scene tiles from the backend
API, renders terrain/structures/vegetation, and supports handoff to
WebXR for Valve Index VR.

## Contracts
- `contracts/backend_to_viewer.yaml` — SceneManifest, SceneTile, EntityMesh, ViewpointList
- `contracts/viewer_to_webxr.yaml` — XRSessionConfig, XRSceneHandoff, XRNavEvent

## Process
1. Read both contract files before writing any code
2. Implement scene loader in `viewer/scene.js`
3. Implement tile manager in `viewer/tiles.js`
4. Implement navigation menu from ViewpointList in `viewer/nav.js`
5. Test with stub data matching the contract test fixtures
6. Verify the scene loads in a browser

## Validation
```bash
HOMEMODEL_MODE=stub npx serve viewer/ &
# Open browser to localhost and verify scene renders
# Check console for no errors
```

## Present
- Screenshot of rendered scene with terrain visible
- Console output showing successful fixture data loading

## Constraints
- Three.js for all rendering
- Y-up coordinate system, meters, origin at scene origin_gps
- Scene origin GPS: lat 42.98743, lon -70.98709, alt_m 26.8
- glTF/GLB for all mesh data
- Viewer is a pure consumer — never writes back to the backend
- Must work with `HOMEMODEL_MODE=stub` (fetch from local fixture files)
- WebXR session shares the Three.js Scene — no scene duplication
