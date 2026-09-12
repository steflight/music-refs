/**
 * MR-15 — Profil de culture musicale (lot E).
 *
 * Enregistrement LOCAL (localStorage, clé `mr:profile`) d'un résultat par citation, puis
 * agrégats purs (testables sans navigateur) : total répondu, % de réussite par catégorie,
 * légendaires trouvées, meilleure série (lue depuis dailyStore) et « grade ».
 *
 * Entrée d'historique :
 *   { quoteId, categoryIds: number[], rarity: 'commune'|'rare'|'legendaire',
 *     outcome: 'correct'|'hint'|'wrong'|'skipped', mode: 'daily'|'solo', day: 'YYYY-MM-DD', ts }
 *
 * Règles documentées :
 *   - « trouvée » = outcome 'correct' (sans indice) ou 'hint' (avec indice) ;
 *     « jouée » = toute entrée (trouvée, ratée ou passée).
 *   - Historique borné à HISTORY_MAX entrées (les plus anciennes sont évincées).
 *   - Une même citation, le même jour, dans le même mode, n'est comptée qu'une fois
 *     (premier résultat conservé) — évite les doublons en cas de rechargement.
 *   - Le profil s'affiche à partir de PROFILE_MIN_ANSWERS citations répondues.
 *   - Grades (taux de réussite en %) :
 *       < 40      → niveau 0 « Curieux·se »
 *       40 – < 70 → niveau 1 « Connaisseur·se »
 *       70 – < 90 → niveau 2 « Expert·e »
 *       ≥ 90      → niveau 3 « Encyclopédie » (ex. « Encyclopédie du Rap FR »)
 *     Un grade de catégorie n'est calculé qu'à partir de MIN_PLAYED_FOR_CATEGORY_GRADE
 *     citations jouées dans la catégorie (sinon `grade: null`).
 *   - Grade principal : la meilleure catégorie éligible (taux le plus haut, puis la plus
 *     jouée) si son niveau ≥ niveau global ; sinon le grade global.
 */
import { getStreak } from './dailyStore.js';

export const PROFILE_KEY = 'mr:profile';
export const HISTORY_MAX = 2000;
export const PROFILE_MIN_ANSWERS = 20;
export const MIN_PLAYED_FOR_CATEGORY_GRADE = 5;
export const OUTCOMES = Object.freeze(['correct', 'hint', 'wrong', 'skipped']);
export const MODES = Object.freeze(['daily', 'solo']);
export const RARITIES = Object.freeze(['commune', 'rare', 'legendaire']);
export const NO_CATEGORY_ID = 0;

/** Seuils de grade, du plus haut au plus bas (min inclus, en %). */
export const GRADE_LEVELS = Object.freeze([
  { level: 3, min: 90, label: 'Encyclopédie', withCategory: (n) => `Encyclopédie du ${n}`, global: 'Encyclopédie musicale' },
  { level: 2, min: 70, label: 'Expert·e', withCategory: (n) => `Expert·e en ${n}`, global: 'Expert·e musical·e' },
  { level: 1, min: 40, label: 'Connaisseur·se', withCategory: (n) => `Connaisseur·se de ${n}`, global: 'Connaisseur·se musical·e' },
  { level: 0, min: 0, label: 'Curieux·se', withCategory: (n) => `Curieux·se de ${n}`, global: 'Curieux·se musical·e' },
]);

function defaultStorage() {
  return typeof localStorage !== 'undefined' ? localStorage : null;
}

/** Date locale YYYY-MM-DD (le daily fournit la sienne, Toronto). */
export function todayIso(d = new Date()) {
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/** Valide et normalise une entrée ; renvoie null si inutilisable. */
export function normalizeEntry(input) {
  if (!input || typeof input !== 'object') return null;
  const quoteId = Number(input.quoteId);
  if (!Number.isFinite(quoteId)) return null;
  const outcome = String(input.outcome || '');
  if (!OUTCOMES.includes(outcome)) return null;
  const mode = MODES.includes(input.mode) ? input.mode : 'solo';
  const rarity = RARITIES.includes(input.rarity) ? input.rarity : 'commune';
  const categoryIds = [...new Set((Array.isArray(input.categoryIds) ? input.categoryIds : [])
    .map(Number)
    .filter((n) => Number.isFinite(n) && n > 0))];
  const day = /^\d{4}-\d{2}-\d{2}$/.test(String(input.day || '')) ? String(input.day) : todayIso();
  const ts = Number.isFinite(Number(input.ts)) ? Number(input.ts) : Date.now();
  return { quoteId, categoryIds, rarity, outcome, mode, day, ts };
}

export function loadHistory(storage = defaultStorage()) {
  if (!storage) return [];
  try {
    const raw = JSON.parse(storage.getItem(PROFILE_KEY) || '[]');
    if (!Array.isArray(raw)) return [];
    return raw.map(normalizeEntry).filter(Boolean);
  } catch (_) {
    return [];
  }
}

export function saveHistory(entries, storage = defaultStorage()) {
  if (!storage) return false;
  try {
    storage.setItem(PROFILE_KEY, JSON.stringify(entries));
    return true;
  } catch (_) {
    return false;
  }
}

export function clearHistory(storage = defaultStorage()) {
  try { storage?.removeItem(PROFILE_KEY); } catch (_) { /* ignore */ }
}

export function entryKey(e) {
  return `${e.mode}|${e.quoteId}|${e.day}`;
}

/**
 * Ajoute une entrée (pure) : dédoublonne sur mode+quoteId+jour (premier résultat conservé)
 * et borne l'historique à `max` en évinçant les plus anciennes.
 */
export function appendEntry(history, entry, max = HISTORY_MAX) {
  const e = normalizeEntry(entry);
  if (!e) return { history: Array.isArray(history) ? history : [], added: false };
  const base = Array.isArray(history) ? history : [];
  const key = entryKey(e);
  if (base.some((h) => entryKey(h) === key)) return { history: base, added: false };
  const next = [...base, e];
  const trimmed = next.length > max ? next.slice(next.length - max) : next;
  return { history: trimmed, added: true };
}

/** Enregistre un résultat dans le stockage local. Renvoie l'entrée ajoutée ou null. */
export function record(input, storage = defaultStorage()) {
  const { history, added } = appendEntry(loadHistory(storage), input);
  if (!added) return null;
  saveHistory(history, storage);
  return history[history.length - 1];
}

export function isFound(entry) {
  return entry.outcome === 'correct' || entry.outcome === 'hint';
}

export function pct(found, played) {
  if (!played) return 0;
  return Math.round((found / played) * 100);
}

/** Niveau de grade pour un taux (%) — voir GRADE_LEVELS. */
export function gradeLevel(ratePct) {
  const r = Number(ratePct) || 0;
  return GRADE_LEVELS.find((g) => r >= g.min) || GRADE_LEVELS[GRADE_LEVELS.length - 1];
}

/** Grade complet : { level, label, title } ; `categoryName` null = grade global. */
export function gradeFor(ratePct, categoryName = null) {
  const g = gradeLevel(ratePct);
  return {
    level: g.level,
    label: g.label,
    title: categoryName ? g.withCategory(categoryName) : g.global,
  };
}

/**
 * Agrégats purs.
 * Renvoie { total, found, foundNoHint, ratePct, legendaryFound, byMode, byCategory }
 * où byCategory = { [id]: { played, found, foundNoHint, ratePct } } (id 0 = sans catégorie).
 */
export function aggregate(history) {
  const list = Array.isArray(history) ? history : [];
  const byCategory = {};
  const byMode = { daily: 0, solo: 0 };
  let found = 0;
  let foundNoHint = 0;
  let legendaryFound = 0;
  for (const e of list) {
    const ok = isFound(e);
    if (ok) found += 1;
    if (e.outcome === 'correct') foundNoHint += 1;
    if (ok && e.rarity === 'legendaire') legendaryFound += 1;
    byMode[e.mode] = (byMode[e.mode] || 0) + 1;
    const ids = e.categoryIds.length ? e.categoryIds : [NO_CATEGORY_ID];
    for (const id of ids) {
      const c = byCategory[id] || (byCategory[id] = { played: 0, found: 0, foundNoHint: 0, ratePct: 0 });
      c.played += 1;
      if (ok) c.found += 1;
      if (e.outcome === 'correct') c.foundNoHint += 1;
      c.ratePct = pct(c.found, c.played);
    }
  }
  return {
    total: list.length,
    found,
    foundNoHint,
    ratePct: pct(found, list.length),
    legendaryFound,
    byMode,
    byCategory,
  };
}

/** Nom d'une catégorie avec repli hors ligne. */
export function categoryName(id, names = {}) {
  const n = Number(id);
  if (n === NO_CATEGORY_ID) return 'Sans catégorie';
  const name = names && (names[n] ?? names[String(n)]);
  return name ? String(name) : `Catégorie #${n}`;
}

/** Meilleure série connue (dailyStore) : max(longestStreak, currentStreak). */
export function getBestStreak() {
  try {
    const s = getStreak();
    return Math.max(Number(s.longestStreak || 0), Number(s.currentStreak || 0));
  } catch (_) {
    return 0;
  }
}

/**
 * Modèle de vue complet pour la page /profil (pur : l'historique, la série et les noms
 * sont injectés).
 */
export function computeProfile(history, { names = {}, bestStreak = 0, minAnswers = PROFILE_MIN_ANSWERS } = {}) {
  const agg = aggregate(history);
  const ready = agg.total >= minAnswers;
  const remaining = Math.max(0, minAnswers - agg.total);
  const globalGrade = gradeFor(agg.ratePct, null);

  const categories = Object.entries(agg.byCategory)
    .map(([id, c]) => {
      const nid = Number(id);
      const name = categoryName(nid, names);
      // Le seau « Sans catégorie » ne porte jamais de grade de catégorie.
      const eligible = nid !== NO_CATEGORY_ID && c.played >= MIN_PLAYED_FOR_CATEGORY_GRADE;
      return {
        id: nid,
        name,
        played: c.played,
        found: c.found,
        foundNoHint: c.foundNoHint,
        ratePct: c.ratePct,
        grade: eligible ? gradeFor(c.ratePct, name) : null,
      };
    })
    .sort((a, b) => b.ratePct - a.ratePct || b.played - a.played || a.name.localeCompare(b.name, 'fr'));

  const best = categories.find((c) => c.grade);
  const mainGrade = best && best.grade.level >= globalGrade.level ? best.grade : globalGrade;

  return {
    ready,
    remaining,
    total: agg.total,
    found: agg.found,
    ratePct: agg.ratePct,
    legendaryFound: agg.legendaryFound,
    byMode: agg.byMode,
    bestStreak: Number(bestStreak) || 0,
    globalGrade,
    mainGrade,
    bestCategory: best || null,
    categories,
  };
}

/** Noms des catégories via l'API ; { } si hors ligne (repli « Catégorie #id »). */
export async function fetchCategoryNames(apiBase = '', fetchImpl = typeof fetch === 'function' ? fetch : null) {
  if (!fetchImpl) return {};
  try {
    const r = await fetchImpl(`${apiBase}/api/music-refs/categories`, { headers: { Accept: 'application/json' } });
    if (!r.ok) return {};
    const data = await r.json();
    const names = {};
    for (const c of Array.isArray(data) ? data : []) {
      if (c && Number.isFinite(Number(c.id))) names[Number(c.id)] = String(c.name || '');
    }
    return names;
  } catch (_) {
    return {};
  }
}
