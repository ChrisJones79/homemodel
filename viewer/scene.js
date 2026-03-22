/**
 * scene.js — Three.js scene setup and initialization.
 *
 * Detects stub mode via ?stub=1 query param or window.HOMEMODEL_MODE === 'stub'.
 * Fetches SceneManifest from the backend (or local fixture in stub mode).
 * Wires up camera, lights, renderer, animation loop, and delegates to
 * tiles.js (mesh loading) and nav.js (viewpoint navigation menu).
 */

import * as THREE from 'three';
import { loadTiles } from './tiles.js';
import { buildNavMenu } from './nav.js';

// ---------------------------------------------------------------------------
// Stub-mode detection
// ---------------------------------------------------------------------------

const _params = new URLSearchParams(location.search);
export const isStubMode =
  _params.get('stub') === '1' ||
  (typeof window !== 'undefined' && window.HOMEMODEL_MODE === 'stub');

// ---------------------------------------------------------------------------
// Renderer
// ---------------------------------------------------------------------------

export const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.xr.enabled = false; // enabled on demand by xr.js

// ---------------------------------------------------------------------------
// Scene
// ---------------------------------------------------------------------------

export const scene = new THREE.Scene();
scene.background = new THREE.Color(0x87ceeb); // sky blue

// ---------------------------------------------------------------------------
// Camera
// ---------------------------------------------------------------------------

export const camera = new THREE.PerspectiveCamera(
  60,
  window.innerWidth / window.innerHeight,
  0.1,
  2000
);
camera.position.set(0, 2, 5);
camera.lookAt(0, 0, 0);

// ---------------------------------------------------------------------------
// Lights
// ---------------------------------------------------------------------------

const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
scene.add(ambientLight);

const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(50, 100, 50);
dirLight.castShadow = true;
dirLight.shadow.mapSize.width = 2048;
dirLight.shadow.mapSize.height = 2048;
dirLight.shadow.camera.near = 0.5;
dirLight.shadow.camera.far = 500;
dirLight.shadow.camera.left = -100;
dirLight.shadow.camera.right = 100;
dirLight.shadow.camera.top = 100;
dirLight.shadow.camera.bottom = -100;
scene.add(dirLight);

// ---------------------------------------------------------------------------
// Resize handler
// ---------------------------------------------------------------------------

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// ---------------------------------------------------------------------------
// GPS → local coordinate conversion
// Exported so that tiles.js, nav.js, and xr.js can share it.
// The function closes over `manifest`; it must not be called before
// `manifest` is populated (i.e. before `init()` resolves).
// ---------------------------------------------------------------------------

const METERS_PER_DEG_LAT = 111320;

/**
 * Convert GPS coordinates to scene-local Cartesian coordinates.
 * Y-up, metres, origin at manifest.origin_gps.
 *
 * @param {number} lat
 * @param {number} lon
 * @param {number} alt_m
 * @returns {{ x: number, y: number, z: number }}
 */
export function gpsToLocal(lat, lon, alt_m) {
  const originLat = manifest.origin_gps.lat;
  const originLon = manifest.origin_gps.lon;
  const originAlt = manifest.origin_gps.alt_m;
  const metersPerDegLon = METERS_PER_DEG_LAT * Math.cos(originLat * Math.PI / 180);
  const x = (lon - originLon) * metersPerDegLon;
  const z = -(lat - originLat) * METERS_PER_DEG_LAT;
  const y = alt_m - originAlt;
  return { x, y, z };
}

// ---------------------------------------------------------------------------
// Manifest (populated during init)
// ---------------------------------------------------------------------------

/** @type {Object} SceneManifest loaded from backend or fixture */
export let manifest = null;

// ---------------------------------------------------------------------------
// Initialisation
// ---------------------------------------------------------------------------

async function init() {
  // 1. Fetch manifest -------------------------------------------------------
  const manifestUrl = isStubMode
    ? './fixtures/scene_manifest.json'
    : '/scene/manifest';

  try {
    const response = await fetch(manifestUrl);
    if (!response.ok) {
      throw new Error(`Manifest fetch failed: ${response.status} ${response.statusText}`);
    }
    manifest = await response.json();
    console.log('[scene] Manifest loaded:', manifest);
  } catch (err) {
    console.error('[scene] Could not load manifest:', err);
    // In stub mode fall back to an empty-but-valid manifest so the viewer
    // still renders the stub geometry.
    manifest = {
      bounds_gps: { sw: { lat: 42.98643, lon: -70.98809 }, ne: { lat: 42.98843, lon: -70.98609 } },
      origin_gps: { lat: 42.98743, lon: -70.98709, alt_m: 26.8 },
      entity_count: 0,
      lod_levels: [],
      last_updated: new Date().toISOString(),
    };
  }

  // 2. Mount renderer -------------------------------------------------------
  const container = document.getElementById('canvas-container');
  if (container) {
    container.appendChild(renderer.domElement);
  } else {
    console.warn('[scene] #canvas-container not found — appending to body');
    document.body.appendChild(renderer.domElement);
  }

  // 3. Load tiles -----------------------------------------------------------
  await loadTiles(manifest);

  // 4. Build nav menu -------------------------------------------------------
  await buildNavMenu(scene, camera);

  // 5. Animation loop -------------------------------------------------------
  renderer.setAnimationLoop(() => {
    renderer.render(scene, camera);
  });

  console.log('[scene] Initialisation complete. Stub mode:', isStubMode);
}

init();
