import { describe, it, expect, beforeEach } from 'vitest';
import {
  PROFILE_KEY, HISTORY_MAX, PROFILE_MIN_ANSWERS, MIN_PLAYED_FOR_CATEGORY_GRADE,
  normalizeEntry, appendEntry, record, loadHistory, aggregate, gradeFor, gradeLevel,
  computeProfile, categoryName, getBestStreak, todayIso, fetchCategoryNames,
} from './profileStore.js';

/** Storage minimal compatible localStorage pour les tests. */
function memStorage(init = {}) {
  const m = new Map(Object.entries(init));
  return {
    get length() { return m.size; },
    key: (i) => [...m.keys()][i] ?? null,
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => m.set(k, String(v)),
    removeItem: (k) => m.delete(k),
    clear: () => m.clear(),
  };
}

const E = (over = {}) => ({
  quoteId: 1, categoryIds: [1], rarity: 'commune', outcome: 'correct', mode: 'daily', day: '2026-09-12', ...over,
});

/** n entrées distinctes (quoteId croissant) avec les surcharges données. */
function many(n, over = {}, start = 1) {
  return Array.from({ length: n }, (_, i) => normalizeEntry(E({ quoteId: start + i, ...over })));
}

describe('MR-15 — normalisation et enregistrement', () => {
  it('normalise une entrée valide et rejette une entrée invalide', () => {
    const e = normalizeEntry({ quoteId: '7', categoryIds: ['2', 2, 'x', -1], rarity: 'rare', outcome: 'hint', mode: 'solo', day: '2026-09-01' });
    expect(e).toMatchObject({ quoteId: 7, categoryIds: [2], rarity: 'rare', outcome: 'hint', mode: 'solo', day: '2026-09-01' });
    expect(typeof e.ts).toBe('number');
    expect(normalizeEntry({ quoteId: 1, outcome: 'nope' })).toBeNull();
    expect(normalizeEntry(null)).toBeNull();
    expect(normalizeEntry({ outcome: 'correct' })).toBeNull();
  });

  it('replie rareté/mode/jour inconnus sur des valeurs sûres', () => {
    const e = normalizeEntry({ quoteId: 1, outcome: 'wrong', rarity: 'divine', mode: 'party', day: 'hier' });
    expect(e.rarity).toBe('commune');
    expect(e.mode).toBe('solo');
    expect(e.day).toBe(todayIso());
  });

  it('record() écrit dans la clé mr:profile et relit', () => {
    const st = memStorage();
    const added = record(E(), st);
    expect(added).toMatchObject({ quoteId: 1, outcome: 'correct' });
    expect(JSON.parse(st.getItem(PROFILE_KEY))).toHaveLength(1);
    expect(loadHistory(st)).toHaveLength(1);
  });

  it('dédoublonne la même citation le même jour dans le même mode (premier résultat gardé)', () => {
    const st = memStorage();
    expect(record(E({ outcome: 'wrong' }), st)).not.toBeNull();
    expect(record(E({ outcome: 'correct' }), st)).toBeNull();
    expect(loadHistory(st)[0].outcome).toBe('wrong');
    // autre mode ou autre jour : compté
    expect(record(E({ mode: 'solo' }), st)).not.toBeNull();
    expect(record(E({ day: '2026-09-13' }), st)).not.toBeNull();
    expect(loadHistory(st)).toHaveLength(3);
  });

  it('ignore un stockage corrompu', () => {
    const st = memStorage({ [PROFILE_KEY]: '{oops' });
    expect(loadHistory(st)).toEqual([]);
    expect(record(E(), st)).not.toBeNull();
  });
});

describe('MR-15 — bornage de l\'historique', () => {
  it(`borne à HISTORY_MAX (${HISTORY_MAX}) en évinçant les plus anciennes`, () => {
    let history = many(HISTORY_MAX);
    expect(history).toHaveLength(HISTORY_MAX);
    const r = appendEntry(history, E({ quoteId: HISTORY_MAX + 1 }));
    expect(r.added).toBe(true);
    expect(r.history).toHaveLength(HISTORY_MAX);
    expect(r.history[0].quoteId).toBe(2); // la plus ancienne (id 1) est partie
    expect(r.history[r.history.length - 1].quoteId).toBe(HISTORY_MAX + 1);
  });

  it('appendEntry accepte un max explicite', () => {
    const r = appendEntry(many(3), E({ quoteId: 99 }), 3);
    expect(r.history.map((e) => e.quoteId)).toEqual([2, 3, 99]);
  });
});

describe('MR-15 — agrégats', () => {
  it('compte total, trouvées (avec ou sans indice), % et légendaires', () => {
    const h = [
      ...many(2, { categoryIds: [1], outcome: 'correct' }, 1),
      ...many(1, { categoryIds: [1], outcome: 'hint' }, 10),
      ...many(1, { categoryIds: [1], outcome: 'wrong' }, 20),
      ...many(1, { categoryIds: [2], outcome: 'skipped' }, 30),
      ...many(1, { categoryIds: [2], outcome: 'correct', rarity: 'legendaire' }, 40),
      ...many(1, { categoryIds: [2], outcome: 'wrong', rarity: 'legendaire' }, 50),
    ];
    const a = aggregate(h);
    expect(a.total).toBe(7);
    expect(a.found).toBe(4);
    expect(a.foundNoHint).toBe(3);
    expect(a.ratePct).toBe(57);
    expect(a.legendaryFound).toBe(1); // la légendaire ratée ne compte pas
    expect(a.byCategory[1]).toEqual({ played: 4, found: 3, foundNoHint: 2, ratePct: 75 });
    expect(a.byCategory[2]).toEqual({ played: 3, found: 1, foundNoHint: 1, ratePct: 33 });
    expect(a.byMode.daily).toBe(7);
  });

  it('une citation multi-catégories compte dans chaque catégorie ; sans catégorie → id 0', () => {
    const a = aggregate([
      normalizeEntry(E({ quoteId: 1, categoryIds: [1, 2] })),
      normalizeEntry(E({ quoteId: 2, categoryIds: [] })),
    ]);
    expect(a.byCategory[1].played).toBe(1);
    expect(a.byCategory[2].played).toBe(1);
    expect(a.byCategory[0].played).toBe(1);
    expect(categoryName(0)).toBe('Sans catégorie');
  });

  it('historique vide → zéros', () => {
    expect(aggregate([])).toMatchObject({ total: 0, found: 0, ratePct: 0, legendaryFound: 0 });
    expect(aggregate(undefined).total).toBe(0);
  });
});

describe('MR-15 — grades', () => {
  it('seuils : <40 Curieux·se, 40–70 Connaisseur·se, 70–90 Expert·e, ≥90 Encyclopédie', () => {
    expect(gradeLevel(0).label).toBe('Curieux·se');
    expect(gradeLevel(39).label).toBe('Curieux·se');
    expect(gradeLevel(40).label).toBe('Connaisseur·se');
    expect(gradeLevel(69).label).toBe('Connaisseur·se');
    expect(gradeLevel(70).label).toBe('Expert·e');
    expect(gradeLevel(89).label).toBe('Expert·e');
    expect(gradeLevel(90).label).toBe('Encyclopédie');
    expect(gradeLevel(100).level).toBe(3);
  });

  it('titre avec catégorie et titre global', () => {
    expect(gradeFor(95, 'Rap FR').title).toBe('Encyclopédie du Rap FR');
    expect(gradeFor(75, 'Pop').title).toBe('Expert·e en Pop');
    expect(gradeFor(50, 'Rock').title).toBe('Connaisseur·se de Rock');
    expect(gradeFor(10, 'Jazz').title).toBe('Curieux·se de Jazz');
    expect(gradeFor(95).title).toBe('Encyclopédie musicale');
  });

  it('repli du nom de catégorie hors ligne', () => {
    expect(categoryName(3, {})).toBe('Catégorie #3');
    expect(categoryName(3, { 3: 'Rap FR' })).toBe('Rap FR');
    expect(categoryName('3', { 3: 'Rap FR' })).toBe('Rap FR');
  });
});

describe('MR-15 — seuil des 20 citations et profil', () => {
  it('sous 20 réponses : pas prêt, N restantes', () => {
    const p = computeProfile(many(19));
    expect(PROFILE_MIN_ANSWERS).toBe(20);
    expect(p.ready).toBe(false);
    expect(p.remaining).toBe(1);
    expect(computeProfile([]).remaining).toBe(20);
  });

  it('à 20 réponses : prêt, catégories triées par taux puis volume', () => {
    const h = [
      ...many(10, { categoryIds: [1], outcome: 'correct' }, 1),       // cat 1 : 100 %
      ...many(5, { categoryIds: [2], outcome: 'wrong' }, 100),        // cat 2 : 0 %
      ...many(5, { categoryIds: [3], outcome: 'hint' }, 200),         // cat 3 : 100 %, moins jouée
    ];
    const p = computeProfile(h, { names: { 1: 'Rap FR', 2: 'Pop', 3: 'Rock' }, bestStreak: 7 });
    expect(p.ready).toBe(true);
    expect(p.remaining).toBe(0);
    expect(p.total).toBe(20);
    expect(p.bestStreak).toBe(7);
    expect(p.categories.map((c) => c.name)).toEqual(['Rap FR', 'Rock', 'Pop']);
    expect(p.categories[0].grade.title).toBe('Encyclopédie du Rap FR');
  });

  it('grade de catégorie null sous MIN_PLAYED_FOR_CATEGORY_GRADE ; grade principal = meilleure catégorie éligible si ≥ global', () => {
    const h = [
      ...many(MIN_PLAYED_FOR_CATEGORY_GRADE - 1, { categoryIds: [9], outcome: 'correct' }, 1), // trop peu jouée
      ...many(10, { categoryIds: [1], outcome: 'correct' }, 100),
      ...many(10, { categoryIds: [2], outcome: 'wrong' }, 200),
    ];
    const p = computeProfile(h, { names: { 1: 'Rap FR', 2: 'Pop' } });
    const c9 = p.categories.find((c) => c.id === 9);
    expect(c9.grade).toBeNull();
    // global : 14/24 = 58 % → Connaisseur·se ; meilleure catégorie éligible : Rap FR 100 % → Encyclopédie
    expect(p.globalGrade.label).toBe('Connaisseur·se');
    expect(p.mainGrade.title).toBe('Encyclopédie du Rap FR');
    expect(p.bestCategory.id).toBe(1);
  });

  it('grade principal = global quand aucune catégorie éligible', () => {
    const p = computeProfile(many(20, { categoryIds: [] }), {});
    // 20/20 sans catégorie : id 0 éligible mais nommée « Sans catégorie »
    expect(p.categories[0].name).toBe('Sans catégorie');
    expect(p.mainGrade.level).toBe(3);
    const p2 = computeProfile(many(20, { categoryIds: [] , outcome: 'wrong' }), {});
    expect(p2.mainGrade.title).toBe('Curieux·se musical·e');
  });
});

describe('MR-15 — série et noms de catégories', () => {
  beforeEach(() => {
    globalThis.localStorage = memStorage();
  });

  it('getBestStreak lit dailyStore (max de longestStreak / currentStreak)', () => {
    globalThis.localStorage.setItem('mr:streak', JSON.stringify({ currentStreak: 3, longestStreak: 9 }));
    expect(getBestStreak()).toBe(9);
    globalThis.localStorage.setItem('mr:streak', JSON.stringify({ currentStreak: 12, longestStreak: 9 }));
    expect(getBestStreak()).toBe(12);
    globalThis.localStorage.removeItem('mr:streak');
    expect(getBestStreak()).toBe(0);
  });

  it('fetchCategoryNames : dictionnaire id → nom, {} hors ligne', async () => {
    const ok = async () => ({ ok: true, json: async () => [{ id: 1, name: 'Rap FR' }, { id: 2, name: 'Pop' }] });
    expect(await fetchCategoryNames('', ok)).toEqual({ 1: 'Rap FR', 2: 'Pop' });
    const ko = async () => { throw new Error('offline'); };
    expect(await fetchCategoryNames('', ko)).toEqual({});
    expect(await fetchCategoryNames('', null)).toEqual({});
  });
});
