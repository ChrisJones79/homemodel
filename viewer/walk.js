/**
 * walk.js — Free-movement camera controller.
 *
 * Provides first-person walk navigation so the user can move anywhere in the
 * scene rather than being limited to pre-defined viewpoints.
 *
 * Controls:
 *   W / Arrow Up    — move forward
 *   S / Arrow Down  — move backward
 *   A / Arrow Left  — strafe left
 *   D / Arrow Right — strafe right
 *   Q / Page Down   — move down
 *   E / Page Up     — move up
 *   Shift           — sprint (3× speed)
 *   Right-click drag — look (yaw + pitch)
 *
 * Usage:
 *   import { initWalk, updateWalk, syncWalkFromCamera } from './walk.js';
 *
 *   // After mounting renderer:
 *   initWalk(camera, renderer.domElement);
 *
 *   // Each animation frame (pass seconds elapsed since last frame):
 *   updateWalk(delta);
 *
 *   // After any external camera repositioning (e.g. viewpoint teleport):
 *   syncWalkFromCamera();
 */

import * as THREE from 'three';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Normal walk speed in metres per second. */
const MOVE_SPEED  = 5.0;

/** Sprint multiplier applied when Shift is held. */
const SPRINT_MULT = 3.0;

/** Mouse look sensitivity in radians per pixel. */
const LOOK_SPEED  = 0.003;

/** Maximum pitch (radians) to prevent flipping past vertical. */
const PITCH_LIMIT = Math.PI / 2 - 0.05;

// ---------------------------------------------------------------------------
// Module state
// ---------------------------------------------------------------------------

/** @type {THREE.Camera|null} */
let _camera = null;

/** @type {HTMLElement|null} */
let _domElement = null;

/** Current horizontal rotation (world Y axis), radians. */
let _yaw = 0;

/** Current vertical rotation (local X axis), radians. */
let _pitch = 0;

/** Tracks which keys are currently held down, keyed by `event.code`. */
const _keys = {};

/** True while right mouse button is held. */
let _isDragging = false;

/** Client X/Y at the start of the current right-click drag. */
let _lastMouseX = 0;
let _lastMouseY = 0;

// Reusable vectors (avoids per-frame allocation).
const _forward = new THREE.Vector3();
const _right   = new THREE.Vector3();
const _worldUp = new THREE.Vector3(0, 1, 0);

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Initialise the walk controller.
 *
 * Must be called once after the renderer DOM element has been mounted.
 * Re-calling replaces the previous camera/element binding.
 *
 * @param {THREE.Camera} camera      The viewer camera to drive.
 * @param {HTMLElement}  domElement  The renderer canvas (for mouse events).
 */
export function initWalk(camera, domElement) {
  _camera     = camera;
  _domElement = domElement;

  // Bootstrap internal orientation from whatever the camera is currently at.
  syncWalkFromCamera();

  domElement.addEventListener('contextmenu', _onContextMenu);
  domElement.addEventListener('mousedown',   _onMouseDown);
  document.addEventListener('mousemove',     _onMouseMove);
  document.addEventListener('mouseup',       _onMouseUp);
  document.addEventListener('keydown',       _onKeyDown);
  document.addEventListener('keyup',         _onKeyUp);

  console.log('[walk] Free-movement controller ready. WASD = move, right-click drag = look.');
}

/**
 * Advance the camera by `delta` seconds based on current key/mouse state.
 *
 * Call this every animation frame before rendering.
 *
 * @param {number} delta  Seconds elapsed since the previous frame.
 */
export function updateWalk(delta) {
  if (!_camera) return;

  // Apply yaw+pitch to the camera quaternion.
  const euler = new THREE.Euler(_pitch, _yaw, 0, 'YXZ');
  _camera.quaternion.setFromEuler(euler);

  // Compute a horizontal-plane forward vector (ignore camera tilt for
  // movement so the user doesn't fly up when looking up).
  _forward.set(0, 0, -1).applyEuler(euler);
  _forward.y = 0;
  if (_forward.lengthSq() > 0) _forward.normalize();

  // Strafe vector is perpendicular to forward on the horizontal plane.
  _right.crossVectors(_forward, _worldUp).negate();
  if (_right.lengthSq() > 0) _right.normalize();

  const speed = (_keys['ShiftLeft'] || _keys['ShiftRight'])
    ? MOVE_SPEED * SPRINT_MULT
    : MOVE_SPEED;
  const dist = speed * delta;

  if (_keys['KeyW']     || _keys['ArrowUp'])    _camera.position.addScaledVector(_forward, dist);
  if (_keys['KeyS']     || _keys['ArrowDown'])  _camera.position.addScaledVector(_forward, -dist);
  if (_keys['KeyA']     || _keys['ArrowLeft'])  _camera.position.addScaledVector(_right,   -dist);
  if (_keys['KeyD']     || _keys['ArrowRight']) _camera.position.addScaledVector(_right,    dist);
  if (_keys['KeyE']     || _keys['PageUp'])     _camera.position.addScaledVector(_worldUp,  dist);
  if (_keys['KeyQ']     || _keys['PageDown'])   _camera.position.addScaledVector(_worldUp, -dist);
}

/**
 * Synchronise the controller's internal yaw/pitch from the camera's current
 * quaternion.  Must be called after any external camera repositioning (e.g.
 * a viewpoint teleport) so that subsequent mouse/key input continues from
 * the new orientation rather than snapping back.
 */
export function syncWalkFromCamera() {
  if (!_camera) return;
  const euler = new THREE.Euler().setFromQuaternion(_camera.quaternion, 'YXZ');
  _yaw   = euler.y;
  _pitch = euler.x;
}

// ---------------------------------------------------------------------------
// Event handlers
// ---------------------------------------------------------------------------

function _onContextMenu(e) {
  // Suppress the browser context menu while the right button is used for look.
  e.preventDefault();
}

function _onMouseDown(e) {
  if (e.button === 2) {
    _isDragging = true;
    _lastMouseX = e.clientX;
    _lastMouseY = e.clientY;
    if (_domElement) _domElement.style.cursor = 'grabbing';
  }
}

function _onMouseMove(e) {
  if (!_isDragging) return;

  const dx = e.clientX - _lastMouseX;
  const dy = e.clientY - _lastMouseY;
  _lastMouseX = e.clientX;
  _lastMouseY = e.clientY;

  _yaw   -= dx * LOOK_SPEED;
  _pitch -= dy * LOOK_SPEED;
  _pitch  = Math.max(-PITCH_LIMIT, Math.min(PITCH_LIMIT, _pitch));
}

function _onMouseUp(e) {
  if (e.button === 2) {
    _isDragging = false;
    if (_domElement) _domElement.style.cursor = '';
  }
}

function _onKeyDown(e) {
  _keys[e.code] = true;
}

function _onKeyUp(e) {
  _keys[e.code] = false;
}
