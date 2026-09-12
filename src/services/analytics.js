/**
 * MR-19 — Analytics sans cookie tiers.
 *
 * API publique (compatible avec l'ancienne version) :
 *   track(name, props)        — enfile un événement (alias : trackEvent)
 *   flush({ beacon })         — envoie la file à POST /api/music-refs/events (≤ 50 par lot)
 *   getPlayerId()             — identifiant joueur anonyme (UUID local, clé `mr:player`, partagée avec dailyStore)
 *   buildBatch(items)         — format du lot envoyé au serveur
 *   configure({ endpoint, flushIntervalMs, autoFlush })
 *   getQueue() / clearQueue() / _resetForTests()
 *
 * Données envoyées : { player_id, tz, events: [{ name, props, ts, path }] } — aucune donnée personnelle
 * (le serveur horodate lui-même et ignore ts/path). Le hook Plausible (window.plausible) est conservé.
 *
 * Stockage local : `mr:analytics:queue` (file d'attente, ≤ 200 événements) et `mr:player` ({ id, pseudo }).
 */
const QUEUE_KEY = 'mr:analytics:queue';
const PLAYER_KEY = 'mr:player';
const QUEUE_MAX = 200;
const BATCH_MAX = 50;
const PROPS_MAX_KEYS = 20;
const PROPS_STR_MAX = 200;

export const EVENT_NAMES = new Set([
  'daily_started',
  'daily_completed',
  'share_clicked',
  'share_landed',
  'streak_milestone',
  'challenge_created',
  'challenge_accepted',
  'notif_optin',
  'quote_submitted',
]);

const config = {
  endpoint: '/api/music-refs/events',
  flushIntervalMs: 10000,
  autoFlush: true,
};

let timer = null;
let listenersBound = false;
let inFlight = false;

export function configure(opts = {}) {
  Object.assign(config, opts);
  return { ...config };
}

function hasStorage() {
  try {
    return typeof localStorage !== 'undefined' && localStorage !== null;
  } catch (_) {
    return false;
  }
}

function readQueue() {
  try {
    if (!hasStorage()) return [];
    const q = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');
    return Array.isArray(q) ? q : [];
  } catch (_) {
    return [];
  }
}

function writeQueue(items) {
  try {
    if (!hasStorage()) return;
    localStorage.setItem(QUEUE_KEY, JSON.stringify(items.slice(-QUEUE_MAX)));
  } catch (_) { /* ignore */ }
}

export function getQueue() {
  return readQueue();
}

export function clearQueue() {
  writeQueue([]);
}

function newId() {
  try {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  } catch (_) { /* ignore */ }
  return `p-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

/** Réutilise l'UUID du daily (`mr:player`), sinon en crée un sous la même clé/forme. */
export function getPlayerId() {
  let player = null;
  try {
    if (hasStorage()) {
      const raw = localStorage.getItem(PLAYER_KEY);
      if (raw) player = JSON.parse(raw);
    }
  } catch (_) { /* ignore */ }
  if (!player || typeof player !== 'object' || !player.id) {
    player = { ...(player && typeof player === 'object' ? player : {}), id: newId(), pseudo: '' };
    try {
      if (hasStorage()) localStorage.setItem(PLAYER_KEY, JSON.stringify(player));
    } catch (_) { /* ignore */ }
  }
  return String(player.id);
}

export function getTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  } catch (_) {
    return 'UTC';
  }
}

function sanitizeProps(props) {
  const out = {};
  if (!props || typeof props !== 'object') return out;
  for (const [k, v] of Object.entries(props).slice(0, PROPS_MAX_KEYS)) {
    if (v === null || typeof v === 'boolean' || typeof v === 'number') out[String(k).slice(0, 32)] = v;
    else if (typeof v === 'string') out[String(k).slice(0, 32)] = v.slice(0, PROPS_STR_MAX);
  }
  return out;
}

export function buildBatch(items) {
  return {
    player_id: getPlayerId(),
    tz: getTimezone(),
    events: items.slice(0, BATCH_MAX).map((e) => ({
      name: e.name,
      props: e.props || {},
      ts: e.ts,
      path: e.path,
    })),
  };
}

function bindListeners() {
  if (listenersBound) return;
  listenersBound = true;
  try {
    if (typeof document !== 'undefined' && document.addEventListener) {
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') flush({ beacon: true });
      });
    }
    if (typeof window !== 'undefined' && window.addEventListener) {
      window.addEventListener('pagehide', () => flush({ beacon: true }));
    }
  } catch (_) { /* ignore */ }
}

function scheduleFlush() {
  if (!config.autoFlush || timer) return;
  timer = setTimeout(() => {
    timer = null;
    flush();
  }, config.flushIntervalMs);
}

function requeue(batch) {
  const rest = readQueue();
  writeQueue(batch.concat(rest));
}

export function track(event, props = {}) {
  const name = String(event || '');
  const clean = sanitizeProps(props);
  try {
    console.info('[mr-analytics]', name, clean);
  } catch (_) { /* ignore */ }
  // Hook Plausible s'il est présent (sans cookie)
  try {
    if (typeof window !== 'undefined' && typeof window.plausible === 'function') {
      window.plausible(name, { props: clean });
    }
  } catch (_) { /* ignore */ }
  if (!EVENT_NAMES.has(name)) {
    try { console.warn('[mr-analytics] événement inconnu ignoré :', name); } catch (_) { /* ignore */ }
    return false;
  }
  const payload = {
    name,
    props: clean,
    ts: new Date().toISOString(),
    path: typeof location !== 'undefined' ? location.pathname + location.search : '',
  };
  const q = readQueue();
  q.push(payload);
  writeQueue(q);
  bindListeners();
  scheduleFlush();
  return true;
}

/** Alias historique. */
export const trackEvent = track;

/**
 * Envoie un lot (≤ 50). `beacon: true` (page qui se cache) → navigator.sendBeacon si disponible,
 * sinon fetch keepalive. En cas d'échec réseau, les événements sont remis en file.
 */
export async function flush({ beacon = false } = {}) {
  const q = readQueue();
  if (!q.length) return true;
  if (inFlight && !beacon) return false;
  const batch = q.slice(0, BATCH_MAX);
  writeQueue(q.slice(BATCH_MAX));
  const body = JSON.stringify(buildBatch(batch));

  if (beacon && typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
    let ok = false;
    try {
      const data = typeof Blob !== 'undefined' ? new Blob([body], { type: 'application/json' }) : body;
      ok = navigator.sendBeacon(config.endpoint, data);
    } catch (_) {
      ok = false;
    }
    if (!ok) requeue(batch);
    if (readQueue().length && ok) return flush({ beacon: true });
    return ok;
  }

  if (typeof fetch !== 'function') {
    requeue(batch);
    return false;
  }
  inFlight = true;
  try {
    const res = await fetch(config.endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      keepalive: true,
      credentials: 'omit',
    });
    // 4xx = lot refusé définitivement (ne pas boucler) ; 5xx/réseau = on réessaiera
    if (!res.ok && res.status >= 500) {
      requeue(batch);
      return false;
    }
  } catch (_) {
    requeue(batch);
    return false;
  } finally {
    inFlight = false;
  }
  if (readQueue().length) scheduleFlush();
  return true;
}

export function _resetForTests() {
  if (timer) clearTimeout(timer);
  timer = null;
  listenersBound = false;
  inFlight = false;
  config.endpoint = '/api/music-refs/events';
  config.flushIntervalMs = 10000;
  config.autoFlush = true;
}

export default { track, trackEvent, flush, getPlayerId, buildBatch, configure };
