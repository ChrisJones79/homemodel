/**
 * browser.js — DB Browser / Asset Inspector module.
 *
 * Exposes initBrowser() which wires up the "Asset Browser" button and the
 * full-screen #browser-overlay panel.  The panel has three columns:
 *
 *   Left   — discovered database list   (GET /databases)
 *   Middle — entity list for a database (GET /databases/{name}/entities)
 *   Right  — isolated 3-D asset preview + attribute key=value editor
 *
 * All property edits are local until "Save" is clicked (PATCH).
 * "Revert" reloads the entity from the API, discarding pending changes.
 * "Save as New DB…" prompts for a name and POSTs to /databases.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { gpsToLocal, manifest } from './scene.js';
import { camera as mainCamera } from './scene.js';
import { syncWalkFromCamera } from './walk.js';

// ---------------------------------------------------------------------------
// Module state
// ---------------------------------------------------------------------------

let _selectedDb     = null;   // DatabaseInfo object  { name, filename, … }
let _selectedId     = null;   // string entity UUID
let _originalEntity = null;   // last loaded entity, unmodified
let _editedProps    = {};     // { 'properties.key': newValue } pending edits

let _previewRenderer  = null;
let _previewScene     = null;
let _previewCamera    = null;
let _previewControls  = null;
let _previewAnimId    = null;
let _previewMeshGroup = null;
let _previewDark      = true;  // true = dark bg, false = light bg

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Wire up all button listeners for the browser overlay.
 * Must be called after the DOM is ready (i.e. after scene.js init).
 */
export function initBrowser() {
  _bind('browser-toggle-btn', 'click', _openBrowser);
  _bind('br-close-btn',       'click', _closeBrowser);
  _bind('br-theme-btn',       'click', _toggleTheme);
  _bind('br-refresh-dbs',     'click', _loadDatabases);
  _bind('br-save-btn',        'click', _saveEntity);
  _bind('br-revert-btn',      'click', _revertEntity);
  _bind('br-save-as-btn',     'click', _saveAsNewDb);
  _bind('br-view-in-place-btn', 'click', _viewInPlace);

  const typeFilter = document.getElementById('br-type-filter');
  if (typeFilter) {
    typeFilter.addEventListener('change', () => {
      if (_selectedDb) {
        _loadEntities(_selectedDb.name, typeFilter.value || null);
      }
    });
  }

  console.log('[browser] Initialised.');
}

// ---------------------------------------------------------------------------
// Overlay open / close
// ---------------------------------------------------------------------------

function _openBrowser() {
  const overlay = document.getElementById('browser-overlay');
  if (overlay) overlay.style.display = 'flex';

  // Initialise the preview renderer the first time the panel opens.
  if (!_previewRenderer) {
    _setupPreviewRenderer();
  } else {
    _startPreviewLoop();
  }

  _loadDatabases();
}

function _closeBrowser() {
  const overlay = document.getElementById('browser-overlay');
  if (overlay) overlay.style.display = 'none';

  if (_previewAnimId !== null) {
    cancelAnimationFrame(_previewAnimId);
    _previewAnimId = null;
  }
}

// ---------------------------------------------------------------------------
// Isolated 3-D preview — separate renderer, scene, and OrbitControls
// ---------------------------------------------------------------------------

function _setupPreviewRenderer() {
  const canvas = document.getElementById('br-preview-canvas');
  if (!canvas) return;

  _previewRenderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  _previewRenderer.setPixelRatio(window.devicePixelRatio);
  _previewRenderer.shadowMap.enabled = true;
  _previewRenderer.shadowMap.type = THREE.PCFSoftShadowMap;

  _previewScene = new THREE.Scene();

  // Ground grid — 40 m × 40 m, 20 divisions
  const grid = new THREE.GridHelper(40, 20, 0x444466, 0x2a2a3a);
  _previewScene.add(grid);

  // Lights
  _previewScene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const sun = new THREE.DirectionalLight(0xffffff, 1.2);
  sun.position.set(10, 20, 10);
  sun.castShadow = true;
  _previewScene.add(sun);

  // Camera
  _previewCamera = new THREE.PerspectiveCamera(55, 1, 0.1, 1000);
  _previewCamera.position.set(8, 6, 12);
  _previewCamera.lookAt(0, 2, 0);

  // Orbit controls
  _previewControls = new OrbitControls(_previewCamera, canvas);
  _previewControls.target.set(0, 2, 0);
  _previewControls.enableDamping = true;
  _previewControls.dampingFactor = 0.08;
  _previewControls.minDistance   = 1;
  _previewControls.maxDistance   = 100;
  _previewControls.update();

  // Resize observer keeps the preview canvas filling its pane
  const pane = canvas.parentElement;
  if (pane) {
    new ResizeObserver(_onPreviewResize).observe(pane);
  }

  _applyPreviewTheme();
  _onPreviewResize();
  _startPreviewLoop();
}

function _onPreviewResize() {
  const pane = document.querySelector('.br-preview-pane');
  if (!pane || !_previewRenderer || !_previewCamera) return;
  const w = pane.clientWidth;
  const h = pane.clientHeight;
  if (w === 0 || h === 0) return;
  _previewRenderer.setSize(w, h, false);
  _previewCamera.aspect = w / h;
  _previewCamera.updateProjectionMatrix();
}

function _startPreviewLoop() {
  if (_previewAnimId !== null) return;
  const loop = () => {
    _previewAnimId = requestAnimationFrame(loop);
    if (_previewControls) _previewControls.update();
    if (_previewRenderer && _previewScene && _previewCamera) {
      _previewRenderer.render(_previewScene, _previewCamera);
    }
  };
  loop();
}

function _applyPreviewTheme() {
  if (!_previewRenderer) return;
  _previewRenderer.setClearColor(_previewDark ? 0x0d0d1a : 0xf0f4f8, 1);
}

// ---------------------------------------------------------------------------
// Database list
// ---------------------------------------------------------------------------

async function _loadDatabases() {
  const listEl = document.getElementById('br-db-list');
  if (!listEl) return;
  listEl.innerHTML = '<p class="br-status">Loading…</p>';

  try {
    const res = await fetch('/databases');
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const data = await res.json();
    _renderDatabaseList(data.databases || []);
  } catch (err) {
    listEl.innerHTML = `<p class="br-status br-error">Error: ${_esc(err.message)}</p>`;
    console.error('[browser] loadDatabases:', err);
  }
}

function _renderDatabaseList(dbs) {
  const listEl = document.getElementById('br-db-list');
  if (!listEl) return;

  if (dbs.length === 0) {
    listEl.innerHTML =
      '<p class="br-status">No databases found.<br>Check SCHEMASTORE_DB_PATH.</p>';
    return;
  }

  listEl.innerHTML = dbs
    .map(
      (db) =>
        `<button class="br-db-card${_selectedDb && _selectedDb.name === db.name ? ' br-selected' : ''}"
                 type="button" data-db="${_esc(db.name)}">
          <span class="br-db-name">${_esc(db.name)}</span>
          <span class="br-db-sub">${_esc(db.filename)}</span>
          <span class="br-db-sub">${db.entity_count} entities · ${_fmtBytes(db.size_bytes)}</span>
        </button>`
    )
    .join('');

  listEl.querySelectorAll('.br-db-card').forEach((btn) => {
    btn.addEventListener('click', () => {
      const db = dbs.find((d) => d.name === btn.dataset.db);
      if (db) _selectDatabase(db);
    });
  });
}

function _selectDatabase(db) {
  _selectedDb  = db;
  _selectedId  = null;
  _originalEntity = null;
  _editedProps = {};

  document.querySelectorAll('.br-db-card').forEach((c) => {
    c.classList.toggle('br-selected', c.dataset.db === db.name);
  });

  const entTitle = document.getElementById('br-entities-title');
  if (entTitle) entTitle.textContent = db.name;

  const entList = document.getElementById('br-entity-list');
  if (entList) entList.innerHTML = '';

  _clearDetailPane();

  const typeFilter = document.getElementById('br-type-filter');
  _loadEntities(db.name, typeFilter ? typeFilter.value || null : null);
}

// ---------------------------------------------------------------------------
// Entity list
// ---------------------------------------------------------------------------

async function _loadEntities(dbName, entityType) {
  const listEl = document.getElementById('br-entity-list');
  if (!listEl) return;
  listEl.innerHTML = '<p class="br-status">Loading…</p>';

  try {
    const params = new URLSearchParams();
    if (entityType) params.set('entity_type', entityType);
    const url = `/databases/${encodeURIComponent(dbName)}/entities${params.toString() ? '?' + params : ''}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const data = await res.json();
    _renderEntityList(dbName, data.entities || []);
    _updateTypeFilter(data.entities || []);
  } catch (err) {
    listEl.innerHTML = `<p class="br-status br-error">Error: ${_esc(err.message)}</p>`;
    console.error('[browser] loadEntities:', err);
  }
}

function _renderEntityList(dbName, entities) {
  const listEl = document.getElementById('br-entity-list');
  if (!listEl) return;

  if (entities.length === 0) {
    listEl.innerHTML = '<p class="br-status">No entities.</p>';
    return;
  }

  listEl.innerHTML = entities
    .map(
      (e) =>
        `<button class="br-entity-row${_selectedId === e.id ? ' br-selected' : ''}"
                 type="button" data-id="${_esc(e.id)}" data-db="${_esc(dbName)}">
          <span class="br-ent-type br-type-${_esc(e.type)}">${_esc(e.type)}</span>
          <span class="br-ent-id">${_esc(e.id.slice(0, 8))}…</span>
          <span class="br-ent-meta">v${e.version} · ${_fmtGPS(e.bounds)}</span>
        </button>`
    )
    .join('');

  listEl.querySelectorAll('.br-entity-row').forEach((btn) => {
    btn.addEventListener('click', () => _selectEntity(btn.dataset.db, btn.dataset.id));
  });
}

function _updateTypeFilter(entities) {
  const select = document.getElementById('br-type-filter');
  if (!select) return;
  const current = select.value;
  const types   = [...new Set(entities.map((e) => e.type))].sort();
  select.innerHTML =
    '<option value="">All types</option>' +
    types
      .map(
        (t) =>
          `<option value="${_esc(t)}"${t === current ? ' selected' : ''}>${_esc(t)}</option>`
      )
      .join('');
}

// ---------------------------------------------------------------------------
// Entity selection → attribute editor + preview
// ---------------------------------------------------------------------------

async function _selectEntity(dbName, entityId) {
  _selectedId  = entityId;
  _editedProps = {};

  document.querySelectorAll('.br-entity-row').forEach((r) => {
    r.classList.toggle('br-selected', r.dataset.id === entityId);
  });

  const attrTitle = document.getElementById('br-attr-title');
  if (attrTitle) attrTitle.textContent = 'Loading…';

  const tableEl = document.getElementById('br-attr-table');
  if (tableEl) tableEl.innerHTML = '<p class="br-status">Loading…</p>';

  try {
    const res = await fetch(
      `/databases/${encodeURIComponent(dbName)}/entities/${encodeURIComponent(entityId)}`
    );
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const entity = await res.json();
    _originalEntity = entity;
    _editedProps    = {};
    _renderAttributeEditor(entity);
    _updatePreviewMesh(entity);
  } catch (err) {
    if (tableEl) tableEl.innerHTML = `<p class="br-status br-error">Error: ${_esc(err.message)}</p>`;
    console.error('[browser] selectEntity:', err);
  }
}

// ---------------------------------------------------------------------------
// Attribute editor
// ---------------------------------------------------------------------------

function _renderAttributeEditor(entity) {
  const attrTitle = document.getElementById('br-attr-title');
  if (attrTitle) {
    const label = entity.type.charAt(0).toUpperCase() + entity.type.slice(1);
    attrTitle.textContent = `${label} — ${entity.id.slice(0, 8)}…`;
  }

  const rows  = _flattenEntity(entity);
  const tbody = rows
    .map(({ key, value, editable }) => {
      const safeKey = _esc(key);
      const safeVal = _esc(String(value ?? ''));
      const cell = editable
        ? `<input class="br-attr-input" type="text" data-key="${safeKey}" value="${safeVal}" />`
        : `<span class="br-attr-ro">${safeVal}</span>`;
      return (
        `<tr class="${editable ? 'br-row-edit' : 'br-row-ro'}">` +
        `<td class="br-attr-key">${safeKey}</td>` +
        `<td class="br-attr-val">${cell}</td>` +
        `<td class="br-attr-copy-cell">` +
        `<button class="br-copy-btn" type="button" data-copy="${safeVal}" title="Copy value">⎘</button>` +
        `</td></tr>`
      );
    })
    .join('');

  const tableEl = document.getElementById('br-attr-table');
  if (!tableEl) return;
  tableEl.innerHTML =
    `<table class="br-kv-table">` +
    `<thead><tr><th>Key</th><th>Value</th><th></th></tr></thead>` +
    `<tbody>${tbody}</tbody></table>`;

  // Copy buttons
  tableEl.querySelectorAll('.br-copy-btn').forEach((btn) => {
    btn.addEventListener('click', () => _copyToClipboard(btn.dataset.copy));
  });

  // Editable inputs — track dirty state and trigger live preview update
  tableEl.querySelectorAll('.br-attr-input').forEach((input) => {
    input.addEventListener('input', () => {
      _editedProps[input.dataset.key] = input.value;
      _setDirty(true);
      _scheduleLiveUpdate();
    });
  });

  _setDirty(false);
  _setEntityLoaded(true);
}

/**
 * Flatten an entity to a list of { key, value, editable } rows.
 *
 * Read-only:  id, type, version, position_gps.*, provenance.*
 * Editable:   properties.*
 */
function _flattenEntity(entity) {
  const rows = [];

  // Top-level scalars
  for (const key of ['id', 'type', 'version']) {
    rows.push({ key, value: entity[key], editable: false });
  }

  // position_gps
  const gps = entity.position_gps ?? {};
  for (const sub of ['lat', 'lon', 'alt_m']) {
    rows.push({ key: `position_gps.${sub}`, value: gps[sub] ?? '', editable: false });
  }

  // provenance
  const prov = entity.provenance ?? {};
  for (const sub of ['source_type', 'source_id', 'timestamp', 'accuracy_m']) {
    if (sub in prov) {
      rows.push({ key: `provenance.${sub}`, value: prov[sub], editable: false });
    }
  }

  // properties — editable
  const props = entity.properties ?? {};
  for (const [k, v] of Object.entries(props)) {
    rows.push({ key: `properties.${k}`, value: v, editable: true });
  }

  return rows;
}

function _clearDetailPane() {
  const attrTitle = document.getElementById('br-attr-title');
  if (attrTitle) attrTitle.textContent = 'Select an entity';

  const tableEl = document.getElementById('br-attr-table');
  if (tableEl) tableEl.innerHTML = '';

  _setDirty(false);
  _setEntityLoaded(false);
  _clearPreviewMesh();

  const gpsEl = document.getElementById('br-preview-gps');
  if (gpsEl) gpsEl.textContent = '';
}

// ---------------------------------------------------------------------------
// 3-D preview mesh
// ---------------------------------------------------------------------------

function _clearPreviewMesh() {
  if (_previewMeshGroup && _previewScene) {
    _previewScene.remove(_previewMeshGroup);
    _previewMeshGroup.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      if (o.material) {
        if (Array.isArray(o.material)) {
          o.material.forEach((m) => m.dispose());
        } else {
          o.material.dispose();
        }
      }
    });
    _previewMeshGroup = null;
  }
}

function _updatePreviewMesh(entity) {
  if (!_previewScene) return;
  _clearPreviewMesh();

  _previewMeshGroup = _buildEntityMesh(entity);
  if (_previewMeshGroup) {
    _previewScene.add(_previewMeshGroup);
  }

  // GPS overlay
  const gps   = entity.position_gps ?? {};
  const gpsEl = document.getElementById('br-preview-gps');
  if (gpsEl && gps.lat != null) {
    const ns = gps.lat >= 0 ? 'N' : 'S';
    const ew = gps.lon >= 0 ? 'E' : 'W';
    gpsEl.textContent =
      `📍 ${Math.abs(gps.lat).toFixed(5)}°${ns}  ${Math.abs(gps.lon).toFixed(5)}°${ew}  ${(gps.alt_m ?? 0).toFixed(1)} m`;
  }
}

/**
 * Build a Three.js Group representing the entity type.
 * Dimensions are derived from entity.properties where available.
 */
function _buildEntityMesh(entity) {
  const type  = entity.type ?? '';
  const props = entity.properties ?? {};
  const group = new THREE.Group();

  if (type === 'tree') {
    const dbh    = Math.max(0.05, (props.dbh_cm ?? 30) / 100);
    const radius = Math.max(0.5, props.canopy_radius_m ?? 3);
    const trunkH = radius * 0.7;

    const trunk = new THREE.Mesh(
      new THREE.CylinderGeometry(dbh * 0.6, dbh, trunkH, 10),
      new THREE.MeshLambertMaterial({ color: 0x5d4037 })
    );
    trunk.position.y = trunkH / 2;
    trunk.castShadow = true;
    group.add(trunk);

    const canopy = new THREE.Mesh(
      new THREE.SphereGeometry(radius, 14, 10),
      new THREE.MeshLambertMaterial({ color: 0x2e7d32 })
    );
    canopy.position.y = trunkH + radius * 0.7;
    canopy.castShadow = true;
    group.add(canopy);

  } else if (type === 'wall') {
    const l = props.length_m    ?? 8;
    const h = props.height_m    ?? 3;
    const t = props.thickness_m ?? 0.3;
    const mesh = new THREE.Mesh(
      new THREE.BoxGeometry(l, h, t),
      new THREE.MeshLambertMaterial({ color: 0xbdbdbd })
    );
    mesh.position.y = h / 2;
    mesh.castShadow = true;
    group.add(mesh);

  } else if (type === 'structure' || type === 'building') {
    const w = props.width_m  ?? 10;
    const d = props.depth_m  ?? 8;
    const h = props.height_m ?? 5;

    const body = new THREE.Mesh(
      new THREE.BoxGeometry(w, h, d),
      new THREE.MeshLambertMaterial({ color: 0xe8d5b7 })
    );
    body.position.y = h / 2;
    body.castShadow = true;
    group.add(body);

    const roofR = Math.max(w, d) * 0.75;
    const roof  = new THREE.Mesh(
      new THREE.ConeGeometry(roofR, h * 0.5, 4),
      new THREE.MeshLambertMaterial({ color: 0x8d6e63 })
    );
    roof.position.y = h + h * 0.25;
    roof.rotation.y = Math.PI / 4;
    roof.castShadow = true;
    group.add(roof);

  } else if (type === 'terrain') {
    const size = props.tile_size_m ?? 20;
    const mesh = new THREE.Mesh(
      new THREE.PlaneGeometry(size, size),
      new THREE.MeshLambertMaterial({ color: 0x8bc34a, side: THREE.DoubleSide })
    );
    mesh.rotation.x = -Math.PI / 2;
    mesh.receiveShadow = true;
    group.add(mesh);

  } else {
    // Generic fallback — a sphere
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(1.5, 16, 12),
      new THREE.MeshLambertMaterial({ color: 0x607d8b })
    );
    mesh.position.y = 1.5;
    mesh.castShadow = true;
    group.add(mesh);
  }

  return group;
}

// Debounced live-preview update when editable inputs change
let _liveUpdateTimer = null;
function _scheduleLiveUpdate() {
  clearTimeout(_liveUpdateTimer);
  _liveUpdateTimer = setTimeout(() => {
    if (_originalEntity) _updatePreviewMesh(_mergeEdits(_originalEntity));
  }, 200);
}

function _mergeEdits(entity) {
  const copy = JSON.parse(JSON.stringify(entity));
  for (const [key, value] of Object.entries(_editedProps)) {
    if (key.startsWith('properties.')) {
      const prop = key.slice('properties.'.length);
      const num  = parseFloat(value);
      copy.properties[prop] = Number.isNaN(num) ? value : num;
    }
  }
  return copy;
}

// ---------------------------------------------------------------------------
// Save / Revert / Save as New DB
// ---------------------------------------------------------------------------

async function _saveEntity() {
  if (!_selectedDb || !_selectedId) return;

  const patchProps = {};
  for (const [key, value] of Object.entries(_editedProps)) {
    if (key.startsWith('properties.')) {
      const prop = key.slice('properties.'.length);
      const num  = parseFloat(value);
      patchProps[prop] = Number.isNaN(num) ? value : num;
    }
  }

  try {
    const res = await fetch(
      `/databases/${encodeURIComponent(_selectedDb.name)}/entities/${encodeURIComponent(_selectedId)}`,
      {
        method:  'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ properties: patchProps }),
      }
    );
    if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
    await _selectEntity(_selectedDb.name, _selectedId);
  } catch (err) {
    alert(`Save failed: ${err.message}`);
    console.error('[browser] save:', err);
  }
}

async function _revertEntity() {
  if (!_selectedDb || !_selectedId) return;
  _editedProps = {};
  await _selectEntity(_selectedDb.name, _selectedId);
}

async function _saveAsNewDb() {
  if (!_selectedDb || !_selectedId || !_originalEntity) return;

  const dbName = prompt(
    'Name for the new database (no path separators, no .db extension):',
    `${_selectedDb.name}_copy`
  );
  if (!dbName || !dbName.trim()) return;

  const merged = _mergeEdits(_originalEntity);

  try {
    const res = await fetch('/databases', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ db_name: dbName.trim(), entity: merged }),
    });
    if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
    const result = await res.json();
    alert(`Created ${result.filename} — entity ${result.entity_id}`);
    _loadDatabases();
  } catch (err) {
    alert(`Save as New DB failed: ${err.message}`);
    console.error('[browser] saveAsNewDb:', err);
  }
}

// ---------------------------------------------------------------------------
// View in Place — teleport main camera to entity GPS location
// ---------------------------------------------------------------------------

function _viewInPlace() {
  if (!_originalEntity) return;
  const gps = _originalEntity.position_gps;
  if (!gps || gps.lat == null) {
    alert('No GPS position available for this entity.');
    return;
  }

  if (!manifest) {
    alert('Scene manifest not yet loaded — try again in a moment.');
    return;
  }

  try {
    const pos = gpsToLocal(gps.lat, gps.lon, gps.alt_m ?? 0);
    // Position camera 3 m above and 8 m behind the entity.
    mainCamera.position.set(pos.x + 8, pos.y + 3, pos.z + 8);
    mainCamera.lookAt(pos.x, pos.y, pos.z);
    syncWalkFromCamera();
    _closeBrowser();
  } catch (err) {
    console.error('[browser] viewInPlace:', err);
    _closeBrowser();
  }
}

// ---------------------------------------------------------------------------
// Theme toggle
// ---------------------------------------------------------------------------

function _toggleTheme() {
  _previewDark = !_previewDark;
  _applyPreviewTheme();
  const btn = document.getElementById('br-theme-btn');
  if (btn) btn.textContent = _previewDark ? '☀️ Light' : '🌙 Dark';
}

// ---------------------------------------------------------------------------
// Clipboard helper
// ---------------------------------------------------------------------------

function _copyToClipboard(value) {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(value).catch(() => _fallbackCopy(value));
  } else {
    _fallbackCopy(value);
  }
}

function _fallbackCopy(value) {
  const ta = document.createElement('textarea');
  ta.value = value;
  ta.style.cssText = 'position:fixed;opacity:0;';
  document.body.appendChild(ta);
  ta.select();
  document.execCommand('copy');
  document.body.removeChild(ta);
}

// ---------------------------------------------------------------------------
// UI state helpers
// ---------------------------------------------------------------------------

function _setDirty(dirty) {
  _setDisabled('br-save-btn',   !dirty);
  _setDisabled('br-revert-btn', !dirty);
}

function _setEntityLoaded(loaded) {
  _setDisabled('br-save-as-btn',      !loaded);
  _setDisabled('br-view-in-place-btn', !loaded);
}

function _setDisabled(id, disabled) {
  const el = document.getElementById(id);
  if (el) el.disabled = disabled;
}

function _bind(id, event, handler) {
  const el = document.getElementById(id);
  if (el) el.addEventListener(event, handler);
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

function _esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function _fmtBytes(bytes) {
  if (bytes < 1024)    return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

function _fmtGPS(bounds) {
  if (!bounds || bounds.lat == null) return '—';
  return `${bounds.lat.toFixed(4)}°, ${bounds.lon.toFixed(4)}°`;
}
