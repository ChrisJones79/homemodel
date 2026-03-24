/**
 * inspect.js — Entity pick / inspect module.
 *
 * Listens for pointerdown events on the renderer canvas.  When the user clicks
 * a mesh that carries a `userData.entityId`, the entity record is fetched from
 * the backend (or the local stub fixture) and displayed in the #inspect-panel
 * overlay.
 *
 * In stub mode each stub mesh has its own fixture file under ./fixtures/ so
 * clicking different objects shows different entity data.
 */

import * as THREE from 'three';
import { isStubMode, renderer, camera, scene } from './scene.js';

// ---------------------------------------------------------------------------
// Internal state
// ---------------------------------------------------------------------------

const _raycaster = new THREE.Raycaster();
const _pointer   = new THREE.Vector2();

// ---------------------------------------------------------------------------
// Stub entity meshes — a small set of visible objects so there is always
// something to click without a live backend.
//
// Each entry maps an entityId to a fixture file and a mesh factory.
// ---------------------------------------------------------------------------

const _STUB_ENTITIES = [
  {
    id: '550e8400-e29b-41d4-a716-446655440000',
    fixture: './fixtures/entity_tree.json',
    name: 'stub-tree-1',
    make: (id) => {
      const trunk = new THREE.CylinderGeometry(0.3, 0.4, 3, 8);
      const mat   = new THREE.MeshLambertMaterial({ color: 0x5d4037 });
      const mesh  = new THREE.Mesh(trunk, mat);
      mesh.position.set(5, 1.5, -5);

      const canopy = new THREE.SphereGeometry(2.5, 10, 8);
      const cmat   = new THREE.MeshLambertMaterial({ color: 0x2e7d32 });
      const crown  = new THREE.Mesh(canopy, cmat);
      crown.position.set(0, 2.5, 0);
      crown.userData.entityId = id;
      mesh.add(crown);
      return mesh;
    },
  },
  {
    id: '550e8400-e29b-41d4-a716-446655440001',
    fixture: './fixtures/entity_tree.json',
    name: 'stub-tree-2',
    make: (id) => {
      const trunk = new THREE.CylinderGeometry(0.25, 0.35, 2.5, 8);
      const mat   = new THREE.MeshLambertMaterial({ color: 0x5d4037 });
      const mesh  = new THREE.Mesh(trunk, mat);
      mesh.position.set(-8, 1.25, -10);

      const canopy = new THREE.SphereGeometry(2.0, 10, 8);
      const cmat   = new THREE.MeshLambertMaterial({ color: 0x388e3c });
      const crown  = new THREE.Mesh(canopy, cmat);
      crown.position.set(0, 2.2, 0);
      crown.userData.entityId = id;
      mesh.add(crown);
      return mesh;
    },
  },
  {
    id: '550e8400-e29b-41d4-a716-446655440002',
    fixture: './fixtures/entity_wall.json',
    name: 'stub-wall',
    make: (_id) => {
      const geo  = new THREE.BoxGeometry(8, 3, 0.3);
      const mat  = new THREE.MeshLambertMaterial({ color: 0xbdbdbd });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(0, 1.5, -15);
      return mesh;
    },
  },
  {
    id: '550e8400-e29b-41d4-a716-446655440003',
    fixture: './fixtures/entity_structure.json',
    name: 'stub-house',
    make: (_id) => {
      const group = new THREE.Group();

      // Main building volume
      const walls = new THREE.BoxGeometry(10, 5, 8);
      const wmat  = new THREE.MeshLambertMaterial({ color: 0xe8d5b7 });
      const body  = new THREE.Mesh(walls, wmat);
      body.position.set(0, 2.5, 0);
      group.add(body);

      // Roof
      const roof = new THREE.ConeGeometry(7.5, 3, 4);
      const rmat = new THREE.MeshLambertMaterial({ color: 0x8d6e63 });
      const apex = new THREE.Mesh(roof, rmat);
      apex.position.set(0, 6.5, 0);
      apex.rotation.y = Math.PI / 4;
      group.add(apex);

      group.position.set(-2, 0, -25);
      return group;
    },
  },
];

/**
 * Add all stub entity meshes to the scene.  Each mesh (or its child) carries
 * the `userData.entityId` used by the raycaster to identify it.
 */
function _addStubEntityMeshes() {
  for (const def of _STUB_ENTITIES) {
    const mesh = def.make(def.id);
    // Tag top-level mesh if no child already set entityId (e.g. tree crown).
    if (!mesh.userData.entityId) {
      mesh.userData.entityId = def.id;
    }
    mesh.name = def.name;
    mesh.castShadow    = true;
    mesh.receiveShadow = true;
    scene.add(mesh);
  }
  console.log(`[inspect] ${_STUB_ENTITIES.length} stub entity meshes added.`);
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
  let url;
  if (isStubMode) {
    // Look up the fixture file for this specific entity id.
    const def = _STUB_ENTITIES.find((e) => e.id === id);
    url = def ? def.fixture : './fixtures/entity_tree.json';
  } else {
    url = `/entities/${encodeURIComponent(id)}`;
  }

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
  // Add stub meshes only in stub mode so there is always something pickable.
  if (isStubMode) {
    _addStubEntityMeshes();
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
