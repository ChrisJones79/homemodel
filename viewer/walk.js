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
 * PS4 / Gamepad controls (Standard Gamepad mapping):
 *   Left  stick     — move (forward / back / strafe)
 *   Right stick     — look (yaw + pitch)
 *   D-pad           — move (forward / back / strafe)
 *   R1  (button 5)  — sprint (3× speed)
 *   R2  (button 7)  — move up
 *   L2  (button 6)  — move down
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

/** Minimum stick axis magnitude that registers as input (avoids drift). */
const GP_DEAD_ZONE  = 0.1;

/** Gamepad look sensitivity in radians per second per full-deflection unit. */
const GP_LOOK_SPEED = 2.0;

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

  console.log('[walk] Free-movement controller ready. WASD = move, right-click drag = look, PS4 gamepad supported.');
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

  // --- Gamepad look (applied before quaternion so it takes effect this frame) ---
  const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
  let _gp = null;
  for (const gp of gamepads) {
    if (gp) { _gp = gp; break; }
  }
  if (_gp) {
    const rx = Math.abs(_gp.axes[2]) > GP_DEAD_ZONE ? _gp.axes[2] : 0;
    const ry = Math.abs(_gp.axes[3]) > GP_DEAD_ZONE ? _gp.axes[3] : 0;
    _yaw   -= rx * GP_LOOK_SPEED * delta;
    _pitch -= ry * GP_LOOK_SPEED * delta;
    _pitch  = Math.max(-PITCH_LIMIT, Math.min(PITCH_LIMIT, _pitch));
  }

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

  // --- Gamepad movement ---
  if (_gp) {
    const gpSprint = _gp.buttons[5]?.pressed ?? false;
    const gpSpeed  = gpSprint ? MOVE_SPEED * SPRINT_MULT : MOVE_SPEED;
    const gpDist   = gpSpeed * delta;

    // Left stick: forward/back (axes[1]) and strafe (axes[0]).
    const lx = Math.abs(_gp.axes[0]) > GP_DEAD_ZONE ? _gp.axes[0] : 0;
    const ly = Math.abs(_gp.axes[1]) > GP_DEAD_ZONE ? _gp.axes[1] : 0;
    if (lx !== 0) _camera.position.addScaledVector(_right,   lx * gpDist);
    if (ly !== 0) _camera.position.addScaledVector(_forward, -ly * gpDist);

    // D-pad: buttons 12–15.
    if (_gp.buttons[12]?.pressed) _camera.position.addScaledVector(_forward,  gpDist);
    if (_gp.buttons[13]?.pressed) _camera.position.addScaledVector(_forward, -gpDist);
    if (_gp.buttons[14]?.pressed) _camera.position.addScaledVector(_right,   -gpDist);
    if (_gp.buttons[15]?.pressed) _camera.position.addScaledVector(_right,    gpDist);

    // R2 (button 7) = move up, L2 (button 6) = move down (analog triggers).
    const r2 = _gp.buttons[7]?.value ?? (_gp.buttons[7]?.pressed ? 1 : 0);
    const l2 = _gp.buttons[6]?.value ?? (_gp.buttons[6]?.pressed ? 1 : 0);
    if (r2 > GP_DEAD_ZONE) _camera.position.addScaledVector(_worldUp,  r2 * gpDist);
    if (l2 > GP_DEAD_ZONE) _camera.position.addScaledVector(_worldUp, -l2 * gpDist);
  }
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
