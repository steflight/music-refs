/** Daily streak + player identity + gel (MR-06, MR-07, MR-12) */

const STREAK_KEY = 'mr:streak';
const PLAYER_KEY = 'mr:player';
const FREEZE_MAX = 2;

export function getPlayer() {
  try {
    const raw = localStorage.getItem(PLAYER_KEY);
    if (raw) return JSON.parse(raw);
  } catch (_) { /* ignore */ }
  const player = {
    id: crypto.randomUUID ? crypto.randomUUID() : `p-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    pseudo: '',
  };
  localStorage.setItem(PLAYER_KEY, JSON.stringify(player));
  return player;
}

export function setPseudo(pseudo) {
  const p = getPlayer();
  p.pseudo = String(pseudo || '').trim().slice(0, 16);
  localStorage.setItem(PLAYER_KEY, JSON.stringify(p));
  return p;
}

export function getStreak() {
  try {
    const s = JSON.parse(localStorage.getItem(STREAK_KEY) || '{}');
    if (typeof s.freezes !== 'number') s.freezes = 1; // 1 gratuit
    if (!Array.isArray(s.freezeMilestonesGranted)) s.freezeMilestonesGranted = [];
    return s;
  } catch (_) {
    return { freezes: 1, freezeMilestonesGranted: [] };
  }
}

function saveStreak(s) {
  localStorage.setItem(STREAK_KEY, JSON.stringify(s));
}

/** Accorde +1 gel tous les 7 jours de série (max 2). */
function grantFreezesForStreak(s, current) {
  const granted = new Set(s.freezeMilestonesGranted || []);
  let freezes = Number(s.freezes ?? 1);
  for (let m = 7; m <= current; m += 7) {
    if (!granted.has(m) && freezes < FREEZE_MAX) {
      freezes += 1;
      granted.add(m);
    } else if (!granted.has(m)) {
      granted.add(m); // milestone vu même si déjà au max
    }
  }
  s.freezes = Math.min(FREEZE_MAX, freezes);
  s.freezeMilestonesGranted = [...granted];
  return s;
}

/**
 * Au chargement : si un jour a été manqué, consomme un gel automatiquement
 * (1 gratuit, +1 / 7 j série, max 2).
 * dateIso = aujourd'hui (Toronto, fourni par l'API).
 */
export function applyStreakFreeze(dateIso) {
  const s = getStreak();
  const last = s.lastCompletedDate || null;
  if (!last || last === dateIso) {
    return {
      currentStreak: Number(s.currentStreak || 0),
      longestStreak: Number(s.longestStreak || 0),
      freezes: Number(s.freezes ?? 1),
      froze: false,
    };
  }

  const prev = new Date(last + 'T12:00:00');
  const cur = new Date(dateIso + 'T12:00:00');
  const diffDays = Math.round((cur - prev) / 86400000);

  if (diffDays <= 1) {
    return {
      currentStreak: Number(s.currentStreak || 0),
      longestStreak: Number(s.longestStreak || 0),
      freezes: Number(s.freezes ?? 1),
      froze: false,
    };
  }

  // Manqué exactement 1 jour → consommer un gel si dispo
  if (diffDays === 2 && Number(s.freezes ?? 1) > 0) {
    s.freezes = Number(s.freezes ?? 1) - 1;
    s.lastFreezeUsedDate = dateIso;
    // Avancer lastCompletedDate d'un jour pour « combler » le trou
    const bridged = new Date(prev);
    bridged.setDate(bridged.getDate() + 1);
    s.lastCompletedDate = bridged.toISOString().slice(0, 10);
    saveStreak(s);
    return {
      currentStreak: Number(s.currentStreak || 0),
      longestStreak: Number(s.longestStreak || 0),
      freezes: s.freezes,
      froze: true,
    };
  }

  // Trop de jours manqués ou plus de gel → reset
  s.currentStreak = 0;
  saveStreak(s);
  return {
    currentStreak: 0,
    longestStreak: Number(s.longestStreak || 0),
    freezes: Number(s.freezes ?? 1),
    froze: false,
  };
}

/** Call when daily set completed (at least 1 answer). dateIso from API (Toronto). */
export function recordDailyCompletion(dateIso) {
  applyStreakFreeze(dateIso);
  const s = getStreak();
  const last = s.lastCompletedDate || null;
  let current = Number(s.currentStreak || 0);
  let longest = Number(s.longestStreak || 0);
  const celebrated = new Set(s.celebratedMilestones || []);

  if (last === dateIso) {
    return {
      currentStreak: current,
      longestStreak: longest,
      lastCompletedDate: last,
      milestone: null,
      freezes: Number(s.freezes ?? 1),
    };
  }

  if (last) {
    const prev = new Date(last + 'T12:00:00');
    const cur = new Date(dateIso + 'T12:00:00');
    const diffDays = Math.round((cur - prev) / 86400000);
    current = diffDays === 1 ? current + 1 : 1;
  } else {
    current = 1;
  }

  if (current > longest) longest = current;

  let milestone = null;
  for (const m of [3, 7, 14, 30, 100]) {
    if (current === m && !celebrated.has(m)) {
      milestone = m;
      celebrated.add(m);
      break;
    }
  }

  const next = grantFreezesForStreak(
    {
      currentStreak: current,
      longestStreak: longest,
      lastCompletedDate: dateIso,
      celebratedMilestones: [...celebrated],
      freezes: Number(s.freezes ?? 1),
      freezeMilestonesGranted: s.freezeMilestonesGranted || [],
      lastFreezeUsedDate: s.lastFreezeUsedDate || null,
    },
    current,
  );
  saveStreak(next);
  return { ...next, milestone };
}

export function dailyStateKey(dateIso, categoryKey) {
  return `mr:daily:${dateIso}:${categoryKey}`;
}

export function loadDailyState(dateIso, categoryKey) {
  try {
    return JSON.parse(localStorage.getItem(dailyStateKey(dateIso, categoryKey)) || 'null');
  } catch (_) {
    return null;
  }
}

export function saveDailyState(dateIso, categoryKey, state) {
  localStorage.setItem(dailyStateKey(dateIso, categoryKey), JSON.stringify(state));
}

export const PROD_ORIGIN = 'https://music-refs.kladriva.ca';

/** Lien du bloc de partage : origine courante + ?ref=share (MR-03 / MR-19). */
export function shareLink(origin) {
  const base = origin
    || (typeof location !== 'undefined' && location.origin && location.origin !== 'null' ? location.origin : '')
    || PROD_ORIGIN;
  return `${String(base).replace(/\/+$/, '')}/daily.html?ref=share`;
}

/**
 * Bloc partageable au format EXACT de la spec MR-03 (4 lignes) :
 *   Music Refs #112 🎤 Rap FR
 *   🟩🟩🟨⬛🟩  4/5
 *   🔥 Série : 7 jours
 *   <origin>/daily.html?ref=share
 * Aucun artiste ni titre. 🟪 = légendaire trouvée (MR-09).
 */
export function buildShareBlock({ edition, categoryName, cells, correct, streak, origin }) {
  const grid = (cells || []).join('');
  const n = Math.max(0, Number(streak) || 0);
  return [
    `Music Refs #${edition} 🎤 ${categoryName}`,
    `${grid}  ${correct}/5`,
    `🔥 Série : ${n} jour${n > 1 ? 's' : ''}`,
    shareLink(origin),
  ].join('\n');
}

/** cell: green | yellow | black | legendary */
export function cellEmoji(kind) {
  if (kind === 'legendary') return '🟪';
  if (kind === 'green') return '🟩';
  if (kind === 'yellow') return '🟨';
  return '⬛';
}

export function prefersReducedMotion() {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch (_) {
    return false;
  }
}

/* ------------------------------------------------------------------ */
/* MR-06 — Série en danger                                             */
/* ------------------------------------------------------------------ */

export const DANGER_HOUR = 20;

/**
 * Vrai si la série (> 0) risque d'être perdue : set du jour non commencé
 * et il est 20 h ou plus en heure LOCALE du navigateur (`now.getHours()`).
 */
export function isStreakInDanger({ now = new Date(), streak = 0, startedToday = false } = {}) {
  if (!(Number(streak) > 0)) return false;
  if (startedToday) return false;
  const d = now instanceof Date ? now : new Date(now);
  return d.getHours() >= DANGER_HOUR;
}

/** Un état de partie compte comme « commencé » dès la 1re réponse (ou s'il est complété). */
export function dailyStateStarted(saved) {
  if (!saved || typeof saved !== 'object') return false;
  if (saved.completed) return true;
  return Array.isArray(saved.cells) && saved.cells.length > 0;
}

/**
 * Le set du jour (toutes catégories confondues) est-il commencé ?
 * Regarde `mr:daily:<dateIso>:*` dans le storage + `lastCompletedDate` de la série.
 */
export function hasStartedToday(dateIso, storage = typeof localStorage !== 'undefined' ? localStorage : null) {
  if (!dateIso || !storage) return false;
  try {
    const st = JSON.parse(storage.getItem(STREAK_KEY) || '{}');
    if (st.lastCompletedDate === dateIso) return true;
  } catch (_) { /* ignore */ }
  const prefix = `mr:daily:${dateIso}:`;
  try {
    for (let i = 0; i < storage.length; i += 1) {
      const k = storage.key(i);
      if (k && k.startsWith(prefix)) {
        let v = null;
        try { v = JSON.parse(storage.getItem(k) || 'null'); } catch (_) { v = null; }
        if (dailyStateStarted(v)) return true;
      }
    }
  } catch (_) { /* ignore */ }
  return false;
}

/* ------------------------------------------------------------------ */
/* MR-02 — Compte à rebours vers minuit America/Toronto                */
/* ------------------------------------------------------------------ */

/** Secondes restantes avant le prochain minuit à Toronto (fonction pure). */
export function secondsToNextToronto(now = new Date()) {
  const d = now instanceof Date ? now : new Date(now);
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Toronto',
    hourCycle: 'h23',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).formatToParts(d);
  const get = (t) => Number(parts.find((p) => p.type === t)?.value || 0);
  const elapsed = (get('hour') % 24) * 3600 + get('minute') * 60 + get('second');
  return Math.max(0, 86400 - elapsed);
}

/** « Prochaines refs dans 06 h 12 » (HH h MM, arrondi à la minute inférieure). */
export function formatCountdown(seconds) {
  const s = Math.max(0, Math.floor(Number(seconds) || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `Prochaines refs dans ${String(h).padStart(2, '0')} h ${String(m).padStart(2, '0')}`;
}

/* ------------------------------------------------------------------ */
/* MR-12 — Validation du pseudo côté client                            */
/* ------------------------------------------------------------------ */

export const PSEUDO_MIN = 3;
export const PSEUDO_MAX = 16;

/** @returns {{ ok: boolean, value: string, error: string|null }} */
export function validatePseudo(raw) {
  const value = String(raw ?? '').trim();
  if (value.length < PSEUDO_MIN) {
    return { ok: false, value, error: `Le pseudo doit faire au moins ${PSEUDO_MIN} caractères.` };
  }
  if (value.length > PSEUDO_MAX) {
    return { ok: false, value, error: `Le pseudo doit faire au plus ${PSEUDO_MAX} caractères.` };
  }
  return { ok: true, value, error: null };
}

/* ------------------------------------------------------------------ */
/* MR-19 — Arrivée via partage (?ref=…), une fois par session          */
/* ------------------------------------------------------------------ */

export const SHARE_LANDED_KEY = 'mr:share_landed';

/**
 * Lit `?ref=` dans `search`. Retourne la valeur si c'est la première
 * arrivée de la session (marque le storage), sinon null.
 */
export function consumeShareRef(search, storage) {
  const ref = (new URLSearchParams(search || '').get('ref') || '').trim();
  if (!ref) return null;
  try {
    if (storage && storage.getItem(SHARE_LANDED_KEY)) return null;
    storage?.setItem(SHARE_LANDED_KEY, ref);
  } catch (_) { /* storage indisponible : on émet quand même */ }
  return ref;
}

/* ------------------------------------------------------------------ */
/* Contrat API (lot A) — helpers purs                                  */
/* ------------------------------------------------------------------ */

/** Grille serveur « 🟩🟨⬛🟪🟩 » → tableau de cases (1 emoji = 1 case). */
export function gridToCells(grid) {
  return typeof grid === 'string' ? Array.from(grid) : [];
}

/** Message lisible depuis `detail` FastAPI (string ou liste Pydantic). */
export function apiErrorMessage(data, fallback = 'Erreur serveur') {
  const d = data && typeof data === 'object' ? data.detail : null;
  if (typeof d === 'string' && d.trim()) return d.trim();
  if (Array.isArray(d)) {
    const msg = d.map((x) => (x && typeof x === 'object' ? x.msg : x) || '').filter(Boolean).join(' ');
    if (msg) return msg;
  }
  return fallback;
}
