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

export function buildShareBlock({ edition, categoryName, cells, correct, streak, freezes }) {
  const grid = cells.join('');
  const lines = [
    `Music Refs #${edition} 🎤 ${categoryName}`,
    `${grid}  ${correct}/5`,
  ];
  if (streak > 0) lines.push(`🔥 Série : ${streak} jour${streak > 1 ? 's' : ''}`);
  if (typeof freezes === 'number' && freezes > 0) {
    lines.push(`🧊 Gel : ${freezes}`);
  }
  lines.push('https://music-refs-dev.kladriva.ca/daily.html?ref=share');
  return lines.join('\n');
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
