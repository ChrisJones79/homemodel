/**
 * debug.js — On-screen debug overlay for the HomeModel viewer.
 *
 * Displays loading status, mode, and errors directly on the canvas so
 * problems are visible without opening the browser console.
 *
 * Usage:
 *   import { debugLog, debugError, debugStep } from './debug.js';
 *
 *   debugStep('manifest', 'loading');
 *   debugStep('manifest', 'ok', '47 entities');
 *   debugError('manifest', 'Fetch failed: 404');
 *   debugLog('Arbitrary message');
 *
 * Toggle visibility with the backtick key (`) or by clicking the panel header.
 */

// ---------------------------------------------------------------------------
// DOM construction (runs once at import time)
// ---------------------------------------------------------------------------

const _panel = document.createElement('div');
_panel.id = 'debug-overlay';
_panel.style.cssText = [
  'position:fixed',
  'bottom:12px',
  'left:12px',
  'z-index:500',
  'background:rgba(0,0,0,0.75)',
  'border:1px solid rgba(255,255,255,0.15)',
  'border-radius:6px',
  'padding:8px 10px',
  'min-width:220px',
  'max-width:320px',
  'font-family:monospace',
  'font-size:11px',
  'color:#ccc',
  'backdrop-filter:blur(3px)',
  'user-select:none',
].join(';');

const _header = document.createElement('div');
_header.style.cssText = [
  'display:flex',
  'justify-content:space-between',
  'align-items:center',
  'margin-bottom:6px',
  'cursor:pointer',
].join(';');
_header.innerHTML =
  '<span style="font-weight:700;color:#e0e0e0;letter-spacing:0.06em;text-transform:uppercase;font-size:10px;">DEBUG</span>' +
  '<span id="debug-toggle-icon" style="color:#888;font-size:10px;">▼ hide</span>';

const _body = document.createElement('div');
_body.id = 'debug-body';

_panel.appendChild(_header);
_panel.appendChild(_body);

// Insert after body is ready.
if (document.body) {
  document.body.appendChild(_panel);
} else {
  document.addEventListener('DOMContentLoaded', () => document.body.appendChild(_panel));
}

// ---------------------------------------------------------------------------
// Collapse / expand
// ---------------------------------------------------------------------------

let _visible = true;

function _setVisible(v) {
  _visible = v;
  _body.style.display = _visible ? 'block' : 'none';
  const icon = document.getElementById('debug-toggle-icon');
  if (icon) icon.textContent = _visible ? '▼ hide' : '▶ show';
}

_header.addEventListener('click', () => _setVisible(!_visible));

document.addEventListener('keydown', (e) => {
  if (e.key === '`') _setVisible(!_visible);
});

// ---------------------------------------------------------------------------
// Internal state
// ---------------------------------------------------------------------------

/** @type {Map<string, {status:string, detail:string, el:HTMLElement}>} */
const _steps = new Map();

/** @type {HTMLElement[]} */
const _logLines = [];
const _MAX_LINES = 6; // keep the last N one-off log messages

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Update (or create) a named status step in the overlay.
 *
 * @param {string} name    Short identifier, e.g. 'manifest'
 * @param {'loading'|'ok'|'warn'|'error'} status
 * @param {string} [detail]  Optional detail text shown after the status icon
 */
export function debugStep(name, status, detail = '') {
  const icons = { loading: '⏳', ok: '✅', warn: '⚠️', error: '❌' };
  const colors = { loading: '#aaa', ok: '#4caf50', warn: '#ff9800', error: '#f44336' };
  const icon  = icons[status]  ?? '•';
  const color = colors[status] ?? '#ccc';

  let entry = _steps.get(name);
  if (!entry) {
    const el = document.createElement('div');
    el.style.cssText = 'margin:2px 0;display:flex;gap:6px;align-items:baseline;';
    _body.insertBefore(el, _body.firstChild);
    entry = { status, detail, el };
    _steps.set(name, entry);
  }

  entry.status = status;
  entry.detail = detail;
  entry.el.innerHTML =
    `<span>${icon}</span>` +
    `<span style="color:${color};font-weight:600;">${_esc(name)}</span>` +
    (detail ? `<span style="color:#999;">${_esc(detail)}</span>` : '');
}

/**
 * Log a one-off message (newest at top, capped at _MAX_LINES).
 *
 * @param {string} msg
 */
export function debugLog(msg) {
  const el = document.createElement('div');
  el.style.cssText = 'margin:1px 0;color:#888;word-break:break-all;';
  el.textContent = msg;

  // Append after step rows (steps are at top via insertBefore).
  _body.appendChild(el);
  _logLines.push(el);
  if (_logLines.length > _MAX_LINES) {
    const old = _logLines.shift();
    old.remove();
  }
}

/**
 * Log an error message (red, also calls debugLog).
 *
 * @param {string} stepName   Matching step name to mark as error
 * @param {string} msg
 */
export function debugError(stepName, msg) {
  debugStep(stepName, 'error', msg);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function _esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
