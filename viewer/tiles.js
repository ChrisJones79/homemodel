/**
 * tiles.js — Scene tile / terrain mesh loader.
 *
 * In stub mode: creates a 100×100 m flat green terrain plane.
 * In live mode: loads the LOD-0 GLB tile from the backend via GLTFLoader.
 */

import * as THREE from 'three';
import { scene, isStubMode } from './scene.js';

// GLTFLoader is only needed in live mode; use a lazy dynamic import so that
// stub mode never tries (and fails) to resolve the CDN path at parse time.
let _GLTFLoader = null;
async function getGLTFLoader() {
  if (!_GLTFLoader) {
    const mod = await import('three/addons/loaders/GLTFLoader.js');
    _GLTFLoader = mod.GLTFLoader;
  }
  return _GLTFLoader;
}

/**
 * Load scene tiles described in the manifest and add them to the scene.
 *
 * @param {Object} manifest  SceneManifest (from scene.js)
 * @returns {Promise<void>}
 */
export async function loadTiles(manifest) {
  if (isStubMode) {
    _loadStubTerrain();
  } else {
    await _loadLiveTile(manifest);
  }
}

// ---------------------------------------------------------------------------
// Stub terrain
// ---------------------------------------------------------------------------

function _loadStubTerrain() {
  const geometry = new THREE.PlaneGeometry(100, 100);
  const material = new THREE.MeshLambertMaterial({ color: 0x4caf50 }); // green
  const plane = new THREE.Mesh(geometry, material);

  // PlaneGeometry is vertical (XY plane) by default; rotate to horizontal.
  plane.rotation.x = -Math.PI / 2;
  plane.receiveShadow = true;
  plane.name = 'stub-terrain';

  scene.add(plane);
  console.log('[tiles] Stub terrain added (100×100 m green plane).');

  // Notify xr.js about the nav mesh (import lazily to avoid circular dep).
  import('./xr.js').then(({ setNavMesh }) => setNavMesh(plane)).catch(() => {});
}

// ---------------------------------------------------------------------------
// Live GLB tile loading
// ---------------------------------------------------------------------------

async function _loadLiveTile(manifest) {
  if (!manifest || !manifest.lod_levels || manifest.lod_levels.length === 0) {
    console.warn('[tiles] No LOD levels in manifest — nothing to load.');
    return;
  }

  const lod0 = manifest.lod_levels[0];
  const url = lod0.mesh_url;

  try {
    const GLTFLoader = await getGLTFLoader();
    const loader = new GLTFLoader();

    await new Promise((resolve, reject) => {
      loader.load(
        url,
        (gltf) => {
          const root = gltf.scene;
          root.name = 'tile-lod0';
          root.traverse((node) => {
            if (node.isMesh) {
              node.castShadow = true;
              node.receiveShadow = true;
            }
          });
          scene.add(root);
          console.log(`[tiles] GLB tile loaded: ${url}`);

          // Pass first mesh found as the nav mesh for XR teleport.
          let navMeshCandidate = null;
          root.traverse((node) => {
            if (node.isMesh && !navMeshCandidate) {
              navMeshCandidate = node;
            }
          });
          if (navMeshCandidate) {
            import('./xr.js')
              .then(({ setNavMesh }) => setNavMesh(navMeshCandidate))
              .catch(() => {});
          }

          resolve();
        },
        undefined,
        (err) => {
          reject(err);
        }
      );
    });
  } catch (err) {
    console.error(`[tiles] Failed to load GLB tile from ${url}:`, err);
  }
}
