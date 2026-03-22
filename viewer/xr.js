/**
 * xr.js — WebXR session management and scene handoff.
 *
 * Handles entering immersive-vr mode, exposing the shared Three.js scene to
 * the WebXR renderer, and processing XRNavEvents (e.g. teleport) from
 * the VR controllers.
 *
 * Contract: viewer_to_webxr.yaml v1
 */

import { scene, camera, renderer } from './scene.js';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

/** ID of the currently active viewpoint (set by nav.js on each teleport). */
let currentViewpointId = 'vp-front-door';

/** Reference to the walkable terrain mesh used for XR teleport ray-casting. */
let navMesh = null;

// ---------------------------------------------------------------------------
// State mutators (called by other modules)
// ---------------------------------------------------------------------------

/**
 * Update the tracked viewpoint ID.  Called by nav.js after each teleport.
 * @param {string} id
 */
export function setCurrentViewpoint(id) {
  currentViewpointId = id;
}

/**
 * Store the nav mesh reference so that getSceneGraph() can expose it.
 * Called by tiles.js once the terrain geometry is ready.
 * @param {THREE.Mesh} mesh
 */
export function setNavMesh(mesh) {
  navMesh = mesh;
}

// ---------------------------------------------------------------------------
// XR session entry
// ---------------------------------------------------------------------------

/**
 * Request an immersive-vr WebXR session and return the XRSessionConfig.
 *
 * @param {THREE.Scene}    _scene     Injected scene (or use module-level import).
 * @param {THREE.Camera}   _camera    Injected camera.
 * @param {THREE.WebGLRenderer} _renderer  Injected renderer.
 * @returns {Promise<Object|null>}  XRSessionConfig, or null if WebXR unavailable.
 */
export async function requestXRSession(_scene, _camera, _renderer) {
  if (!navigator.xr) {
    console.warn('[xr] WebXR not available in this browser.');
    return null;
  }

  /** @type {XRSessionConfig} */
  const config = {
    mode: 'immersive-vr',
    reference_space: 'local-floor',
    initial_viewpoint_id: currentViewpointId,
    render_scale: 1.0,
    controller_mapping: 'valve_index',
  };

  const supported = await navigator.xr.isSessionSupported('immersive-vr').catch(() => false);
  if (!supported) {
    console.warn('[xr] immersive-vr not supported on this device.');
    return null;
  }

  try {
    const activeRenderer = _renderer || renderer;
    activeRenderer.xr.enabled = true;
    activeRenderer.xr.setReferenceSpaceType('local-floor');

    const session = await navigator.xr.requestSession('immersive-vr', {
      optionalFeatures: ['local-floor', 'hand-tracking'],
    });

    await activeRenderer.xr.setSession(session);

    console.log('[xr] Immersive-VR session started. Config:', config);
    return config;
  } catch (err) {
    console.error('[xr] Failed to start XR session:', err);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Scene handoff
// ---------------------------------------------------------------------------

/**
 * Build an XRSceneHandoff object for the WebXR renderer.
 * The Three.js Scene is shared (not duplicated).
 *
 * @param {THREE.Scene}  _scene
 * @param {THREE.Camera} _camera
 * @returns {Object}  XRSceneHandoff
 */
export function getSceneGraph(_scene, _camera) {
  const activeScene = _scene || scene;
  const activeCamera = _camera || camera;

  return {
    scene: activeScene,
    camera_rig: {
      position: activeCamera.position.clone(),
      rotation: activeCamera.rotation.clone(),
    },
    nav_mesh: navMesh,
    interaction_targets: [],
  };
}

// ---------------------------------------------------------------------------
// XRNavEvent handler
// ---------------------------------------------------------------------------

/**
 * Handle an XRNavEvent dispatched by the WebXR renderer.
 *
 * Supported event types:
 *   - teleport  → moves camera to target_position_local + 1.7 m eye height
 *
 * @param {Object} event  XRNavEvent
 */
export function handleNav(event) {
  console.log(`[xr] handleNav: type="${event.type}" controller="${event.controller}"`);

  if (event.type === 'teleport') {
    const { x, y, z } = event.target_position_local;
    camera.position.set(x, y + 1.7, z);
    console.log(`[xr] Teleported to local (${x}, ${y + 1.7}, ${z})`);
  }
}
