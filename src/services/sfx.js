/**
 * Lightweight SFX via Web Audio API (no copyrighted audio files).
 * Persist mute in localStorage. Unlock AudioContext on first user gesture.
 */

const STORAGE_KEY = 'music_refs_sfx_on';

let ctx = null;
let unlocked = false;

function prefersQuiet() {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch (_) {
    return false;
  }
}

export function isSfxEnabled() {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === null) return false; // coupé par défaut (MR-10), mémorisé ensuite
    return v === '1';
  } catch (_) {
    return false;
  }
}

export function setSfxEnabled(on) {
  try {
    localStorage.setItem(STORAGE_KEY, on ? '1' : '0');
  } catch (_) { /* ignore */ }
  syncSfxButtons();
}

export function toggleSfx() {
  const next = !isSfxEnabled();
  setSfxEnabled(next);
  if (next) playSuccess(); // preview on enable
  return next;
}

function ensureCtx() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
  }
  if (ctx.state === 'suspended') {
    ctx.resume().catch(() => {});
  }
  unlocked = true;
  return ctx;
}

/** Call once from a click/tap so browsers allow audio. */
export function unlockSfx() {
  ensureCtx();
}

function tone(freq, durationMs, type = 'sine', gain = 0.08, when = 0) {
  const audio = ensureCtx();
  if (!audio || !isSfxEnabled()) return;
  const t0 = audio.currentTime + when;
  const osc = audio.createOscillator();
  const g = audio.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, t0);
  g.gain.setValueAtTime(0.0001, t0);
  g.gain.exponentialRampToValueAtTime(gain, t0 + 0.015);
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + durationMs / 1000);
  osc.connect(g);
  g.connect(audio.destination);
  osc.start(t0);
  osc.stop(t0 + durationMs / 1000 + 0.02);
}

/** Full guess / win */
export function playSuccess() {
  tone(523.25, 90, 'triangle', 0.07, 0); // C5
  tone(659.25, 110, 'triangle', 0.07, 0.08); // E5
  tone(783.99, 160, 'triangle', 0.08, 0.16); // G5
}

/** Partial correct (artist XOR title) */
export function playPartial() {
  tone(587.33, 100, 'sine', 0.06, 0); // D5
  tone(698.46, 120, 'sine', 0.06, 0.09); // F5
}

/** Wrong answer */
export function playError() {
  tone(180, 140, 'sawtooth', 0.045, 0);
  tone(140, 180, 'sawtooth', 0.04, 0.05);
}

/** Streak bump (combo or daily later) */
export function playStreak() {
  tone(440, 70, 'square', 0.035, 0);
  tone(554.37, 70, 'square', 0.035, 0.06);
  tone(659.25, 100, 'square', 0.04, 0.12);
}

export function syncSfxButtons() {
  const on = isSfxEnabled();
  document.querySelectorAll('[data-sfx-toggle]').forEach((btn) => {
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    btn.title = on ? 'Son activé — cliquer pour couper' : 'Son coupé — cliquer pour activer';
    btn.textContent = on ? '🔊' : '🔇';
  });
}

export function bindSfxToggle(root = document) {
  root.querySelectorAll('[data-sfx-toggle]').forEach((btn) => {
    if (btn.dataset.sfxBound) return;
    btn.dataset.sfxBound = '1';
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      unlockSfx();
      toggleSfx();
    });
  });
  // Unlock on first interaction anywhere
  const once = () => {
    unlockSfx();
    document.removeEventListener('pointerdown', once);
    document.removeEventListener('keydown', once);
  };
  document.addEventListener('pointerdown', once, { once: true });
  document.addEventListener('keydown', once, { once: true });
  syncSfxButtons();
}
