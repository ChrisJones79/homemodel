/**
 * inspect.js — Entity pick / inspect module.
 *
 * Listens for pointerdown events on the renderer canvas.  When the user clicks
 * a mesh that carries a `userData.entityId`, the entity record is fetched from
 * the backend (or the local stub fixture) and displayed in the #inspect-panel
 * overlay.
 *
 * In stub mode the actual entity id is ignored and ./fixtures/entity_tree.json
 * is always returned so that the panel can be exercised without a live backend.
 */

import * as THREE from 'three';
import { isStubMode, renderer, camera, scene } from './scene.js';

// ---------------------------------------------------------------------------
// Internal state
// ---------------------------------------------------------------------------

const _raycaster = new THREE.Raycaster();
const _pointer   = new THREE.Vector2();

// ---------------------------------------------------------------------------
// Stub entity mesh — a small orange box so there is always something to click
// in stub mode.
// ---------------------------------------------------------------------------

function _addStubEntityMesh() {
  const geometry = new THREE.BoxGeometry(2, 3, 2);
  const material = new THREE.MeshLambertMaterial({ color: 0xff6d00 });
  const mesh     = new THREE.Mesh(geometry, material);

  mesh.position.set(5, 1.5, -5);
  mesh.castShadow    = true;
  mesh.receiveShadow = true;
  mesh.name          = 'stub-entity';
  mesh.userData.entityId = '550e8400-e29b-41d4-a716-446655440000';

  scene.add(mesh);
  console.log('[inspect] Stub entity mesh added at (5, 1.5, −5).');
}

// ---------------------------------------------------------------------------
// Entity fetch
// ---------------------------------------------------------------------------

/**
 * Fetch an entity record by id.
 *
 * In stub mode the id is ignored and the local fixture is returned.
 *
 * @param {string} id  Entity UUID
 * @returns {Promise<Object>}
 */
async function fetchEntity(id) {
  const url = isStubMode
    ? './fixtures/entity_tree.json'
    : `/entities/${encodeURIComponent(id)}`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Entity fetch failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

// ---------------------------------------------------------------------------
// Panel helpers
// ---------------------------------------------------------------------------

/**
 * Populate and show the #inspect-panel overlay with data from `entity`.
 *
 * @param {Object} entity  Entity record from backend / fixture
 */
function showPanel(entity) {
  const panel = document.getElementById('inspect-panel');
  if (!panel) return;

  // Title
  const title = document.getElementById('inspect-title');
  if (title) {
    title.textContent = entity.type
      ? entity.type.charAt(0).toUpperCase() + entity.type.slice(1)
      : 'Entity';
  }

  // Meta — id and type
  const meta = document.getElementById('inspect-meta');
  if (meta) {
    meta.innerHTML =
      `<span class="inspect-meta-label">ID</span>` +
      `<span class="inspect-meta-value">${_esc(entity.id ?? '—')}</span>` +
      `<span class="inspect-meta-label">Type</span>` +
      `<span class="inspect-meta-value">${_esc(entity.type ?? '—')}</span>`;
  }

  // Properties
  const propsEl = document.getElementById('inspect-props');
  if (propsEl) {
    const props = entity.properties ?? {};
    const entries = Object.entries(props);
    if (entries.length === 0) {
      propsEl.innerHTML = '<span class="inspect-no-props">No properties.</span>';
    } else {
      propsEl.innerHTML =
        '<table class="inspect-table">' +
        entries
          .map(
            ([k, v]) =>
              `<tr><th>${_esc(k)}</th><td>${_esc(String(v))}</td></tr>`
          )
          .join('') +
        '</table>';
    }
  }

  panel.style.display = 'block';
}

/** Hide the #inspect-panel overlay. */
function hidePanel() {
  const panel = document.getElementById('inspect-panel');
  if (panel) {
    panel.style.display = 'none';
  }
}

/** Minimal HTML-escape to avoid injecting raw entity data into innerHTML. */
function _esc(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ---------------------------------------------------------------------------
// Event handlers
// ---------------------------------------------------------------------------

function _onPointerDown(event) {
  // Ignore if the click was on a UI overlay, not the canvas.
  if (event.target !== renderer.domElement) return;

  // Convert pointer position to normalised device coordinates (−1..+1).
  const rect = renderer.domElement.getBoundingClientRect();
  _pointer.x =  ((event.clientX - rect.left) / rect.width)  * 2 - 1;
  _pointer.y = -((event.clientY - rect.top)  / rect.height) * 2 + 1;

  _raycaster.setFromCamera(_pointer, camera);

  const intersects = _raycaster.intersectObjects(scene.children, true);

  // Walk intersections from nearest to farthest; stop at first entity mesh.
  for (const hit of intersects) {
    const entityId = hit.object.userData?.entityId;
    if (entityId) {
      console.log('[inspect] Hit entity:', entityId);
      fetchEntity(entityId)
        .then((entity) => showPanel(entity))
        .catch((err) => console.error('[inspect] fetchEntity error:', err));
      return; // handled
    }
  }

  // Clicking empty space closes any open panel.
  hidePanel();
}

function _onKeyDown(event) {
  if (event.key === 'Escape') {
    hidePanel();
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Wire up click and keyboard listeners for entity inspection.
 * Must be called after tiles and nav are initialised (i.e. from scene.js
 * before the animation loop starts, once the scene is fully populated).
 */
export function initInspect() {
  // Add stub mesh only in stub mode so there is always something pickable.
  if (isStubMode) {
    _addStubEntityMesh();
  }

  // Canvas pointer handler — listen on window so we can compare event.target.
  window.addEventListener('pointerdown', _onPointerDown);

  // Keyboard: Escape closes the panel.
  document.addEventListener('keydown', _onKeyDown);

  // Panel close button.
  const closeBtn = document.getElementById('inspect-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', hidePanel);
  }

  console.log('[inspect] Initialised.');
}
