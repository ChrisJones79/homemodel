/**
 * nav.js — Viewpoint navigation menu.
 *
 * Fetches the ViewpointList and builds a HTML nav menu.
 * Each button teleports the camera to the corresponding GPS viewpoint.
 */

import { gpsToLocal, isStubMode } from './scene.js';
import { syncWalkFromCamera } from './walk.js';
import { debugStep } from './debug.js';

/** @type {Array} ViewpointList.viewpoints after fetch */
export let viewpoints = [];

/**
 * Fetch viewpoints and build the navigation menu.
 *
 * @param {THREE.Scene}  _scene   Passed for API symmetry; not used directly.
 * @param {THREE.Camera} camera   The viewer camera to reposition on click.
 * @returns {Promise<void>}
 */
export async function buildNavMenu(_scene, camera) {
  const url = isStubMode ? './fixtures/viewpoints.json' : '/nav/viewpoints';

  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Viewpoints fetch failed: ${response.status} ${response.statusText}`);
    }
    const data = await response.json();
    viewpoints = data.viewpoints || [];
    debugStep('nav', 'ok', `${viewpoints.length} viewpoint(s)`);
    console.log(`[nav] Loaded ${viewpoints.length} viewpoint(s).`);
  } catch (err) {
    debugStep('nav', 'error', err.message);
    console.error('[nav] Could not load viewpoints:', err);
    viewpoints = [];
  }

  _buildMenu(camera);
}

// ---------------------------------------------------------------------------
// DOM construction
// ---------------------------------------------------------------------------

function _buildMenu(camera) {
  const container = document.getElementById('nav-menu');
  if (!container) {
    console.warn('[nav] #nav-menu element not found — skipping menu build.');
    return;
  }

  // Clear any previous content.
  container.innerHTML = '';

  if (viewpoints.length === 0) {
    const empty = document.createElement('p');
    empty.textContent = 'No viewpoints available.';
    empty.style.cssText = 'color:#aaa;margin:4px 0;font-size:12px;';
    container.appendChild(empty);
    return;
  }

  viewpoints.forEach((vp) => {
    const btn = document.createElement('button');
    btn.textContent = vp.label;
    btn.dataset.vpId = vp.id;
    btn.classList.add('nav-btn');
    if (vp.indoor) {
      btn.classList.add('nav-btn--indoor');
    }

    btn.addEventListener('click', () => _teleportTo(vp, camera));
    container.appendChild(btn);
  });
}

// ---------------------------------------------------------------------------
// Camera teleport
// ---------------------------------------------------------------------------

function _teleportTo(vp, camera) {
  const pos = gpsToLocal(
    vp.position_gps.lat,
    vp.position_gps.lon,
    vp.position_gps.alt_m
  );

  // Ensure eye height is at least 1.7 m above ground.
  const eyeY = Math.max(pos.y, 1.7);
  camera.position.set(pos.x, eyeY, pos.z);

  const lookAt = gpsToLocal(
    vp.look_at_gps.lat,
    vp.look_at_gps.lon,
    vp.look_at_gps.alt_m
  );
  camera.lookAt(lookAt.x, lookAt.y, lookAt.z);

  console.log(`[nav] Teleported to "${vp.label}" → local (${pos.x.toFixed(2)}, ${eyeY.toFixed(2)}, ${pos.z.toFixed(2)})`);

  // Keep walk controller in sync so mouse/key input continues from the
  // new orientation rather than snapping back to the old one.
  syncWalkFromCamera();

  // Sync XR viewpoint tracker if available.
  import('./xr.js')
    .then(({ setCurrentViewpoint }) => setCurrentViewpoint(vp.id))
    .catch(() => {});
}
