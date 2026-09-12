import { describe, it, expect, beforeEach } from 'vitest';
import {
  isStreakInDanger, dailyStateStarted, hasStartedToday,
  buildShareBlock, shareLink, cellEmoji,
  secondsToNextToronto, formatCountdown,
  validatePseudo, consumeShareRef, SHARE_LANDED_KEY,
  gridToCells, apiErrorMessage,
} from './dailyStore.js';

/** Storage minimal compatible localStorage/sessionStorage pour les tests. */
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

describe('MR-06 — série en danger', () => {
  const at = (h, m = 0) => new Date(2026, 8, 12, h, m, 0); // heure LOCALE

  it('affichée à 20 h locale si série > 0 et set non commencé', () => {
    expect(isStreakInDanger({ now: at(20, 0), streak: 3, startedToday: false })).toBe(true);
    expect(isStreakInDanger({ now: at(23, 59), streak: 1, startedToday: false })).toBe(true);
  });

  it('masquée avant 20 h', () => {
    expect(isStreakInDanger({ now: at(19, 59), streak: 3, startedToday: false })).toBe(false);
    expect(isStreakInDanger({ now: at(8), streak: 3, startedToday: false })).toBe(false);
  });

  it('masquée si série nulle ou set déjà commencé', () => {
    expect(isStreakInDanger({ now: at(21), streak: 0, startedToday: false })).toBe(false);
    expect(isStreakInDanger({ now: at(21), streak: 5, startedToday: true })).toBe(false);
  });

  it('un état est « commencé » dès la 1re réponse ou s’il est complété', () => {
    expect(dailyStateStarted(null)).toBe(false);
    expect(dailyStateStarted({ completed: false, cells: [] })).toBe(false);
    expect(dailyStateStarted({ completed: false, cells: ['🟩'] })).toBe(true);
    expect(dailyStateStarted({ completed: true, cells: [] })).toBe(true);
  });

  it('hasStartedToday scanne mr:daily:<date>:* et lastCompletedDate', () => {
    const empty = memStorage({ 'mr:daily:2026-09-11:all': JSON.stringify({ cells: ['🟩'] }) });
    expect(hasStartedToday('2026-09-12', empty)).toBe(false);
    const started = memStorage({ 'mr:daily:2026-09-12:cat:3': JSON.stringify({ cells: ['⬛'] }) });
    expect(hasStartedToday('2026-09-12', started)).toBe(true);
    const done = memStorage({ 'mr:streak': JSON.stringify({ currentStreak: 2, lastCompletedDate: '2026-09-12' }) });
    expect(hasStartedToday('2026-09-12', done)).toBe(true);
  });
});

describe('MR-03 — bloc de partage', () => {
  it('respecte le format exact des 4 lignes de la spec', () => {
    const block = buildShareBlock({
      edition: 112,
      categoryName: 'Rap FR',
      cells: ['🟩', '🟩', '🟨', '⬛', '🟩'],
      correct: 4,
      streak: 7,
      origin: 'https://music-refs.kladriva.ca',
    });
    expect(block).toBe([
      'Music Refs #112 🎤 Rap FR',
      '🟩🟩🟨⬛🟩  4/5',
      '🔥 Série : 7 jours',
      'https://music-refs.kladriva.ca/daily.html?ref=share',
    ].join('\n'));
    expect(block.split('\n')).toHaveLength(4);
  });

  it('accorde « jour » au singulier et ne contient ni artiste ni titre', () => {
    const block = buildShareBlock({
      edition: 5, categoryName: 'Toutes', cells: ['⬛', '⬛', '⬛', '⬛', '⬛'], correct: 0, streak: 1, origin: 'http://localhost:8084',
    });
    expect(block).toContain('🔥 Série : 1 jour\n');
    expect(block).not.toMatch(/Ninho|Booba/);
  });

  it('utilise 🟪 pour une légendaire trouvée', () => {
    expect(cellEmoji('legendary')).toBe('🟪');
    const cells = ['green', 'yellow', 'black', 'legendary', 'green'].map(cellEmoji);
    const block = buildShareBlock({ edition: 1, categoryName: 'Rap FR', cells, correct: 4, streak: 2, origin: 'https://a.b' });
    expect(block.split('\n')[1]).toBe('🟩🟨⬛🟪🟩  4/5');
  });

  it('le lien est ${origin}/daily.html?ref=share, sans domaine dev en dur', () => {
    expect(shareLink('https://music-refs-dev.kladriva.ca')).toBe('https://music-refs-dev.kladriva.ca/daily.html?ref=share');
    expect(shareLink('http://localhost:8084/')).toBe('http://localhost:8084/daily.html?ref=share');
    expect(shareLink()).toBe('https://music-refs.kladriva.ca/daily.html?ref=share'); // hors navigateur : prod
  });
});

describe('MR-02 — compte à rebours minuit America/Toronto', () => {
  it('formate en « Prochaines refs dans HH h MM »', () => {
    expect(formatCountdown(6 * 3600 + 12 * 60 + 45)).toBe('Prochaines refs dans 06 h 12');
    expect(formatCountdown(0)).toBe('Prochaines refs dans 00 h 00');
    expect(formatCountdown(-5)).toBe('Prochaines refs dans 00 h 00');
    expect(formatCountdown(23 * 3600 + 59 * 60 + 59)).toBe('Prochaines refs dans 23 h 59');
  });

  it('calcule depuis minuit Toronto, pas minuit local (EDT, UTC-4)', () => {
    // 01:48:00Z le 13/09 = 21:48 EDT le 12/09 à Toronto → 2 h 12 avant minuit
    const s = secondsToNextToronto(new Date('2026-09-13T01:48:00Z'));
    expect(s).toBe(2 * 3600 + 12 * 60);
    expect(formatCountdown(s)).toBe('Prochaines refs dans 02 h 12');
  });

  it('gère l’heure d’hiver (EST, UTC-5) et le passage de minuit', () => {
    // 05:00:00Z le 15/01 = 00:00 EST → journée entière
    expect(secondsToNextToronto(new Date('2026-01-15T05:00:00Z'))).toBe(86400);
    // 04:59:30Z = 23:59:30 EST → 30 s
    expect(secondsToNextToronto(new Date('2026-01-15T04:59:30Z'))).toBe(30);
  });
});

describe('MR-12 — validation du pseudo', () => {
  it('accepte 3 à 16 caractères après trim', () => {
    expect(validatePseudo('  Lex  ')).toEqual({ ok: true, value: 'Lex', error: null });
    expect(validatePseudo('ABCDEFGHIJKLMNOP')).toMatchObject({ ok: true, value: 'ABCDEFGHIJKLMNOP' });
  });

  it('refuse trop court / trop long avec un message français', () => {
    expect(validatePseudo(' ab ')).toEqual({ ok: false, value: 'ab', error: 'Le pseudo doit faire au moins 3 caractères.' });
    expect(validatePseudo('')).toMatchObject({ ok: false });
    expect(validatePseudo(null)).toMatchObject({ ok: false });
    expect(validatePseudo('ABCDEFGHIJKLMNOPQ')).toEqual({
      ok: false, value: 'ABCDEFGHIJKLMNOPQ', error: 'Le pseudo doit faire au plus 16 caractères.',
    });
  });
});

describe('MR-19 — share_landed une fois par session', () => {
  let session;
  beforeEach(() => { session = memStorage(); });

  it('retourne le ref à la première arrivée puis null dans la même session', () => {
    expect(consumeShareRef('?ref=share', session)).toBe('share');
    expect(session.getItem(SHARE_LANDED_KEY)).toBe('share');
    expect(consumeShareRef('?ref=share', session)).toBeNull();
    expect(consumeShareRef('?ref=whatsapp', session)).toBeNull();
  });

  it('accepte tout ?ref= et ignore l’absence de paramètre', () => {
    expect(consumeShareRef('?category=3&ref=wa', session)).toBe('wa');
    expect(consumeShareRef('', memStorage())).toBeNull();
    expect(consumeShareRef('?category=3', memStorage())).toBeNull();
  });
});

describe('Contrat API lot A — helpers', () => {
  it('gridToCells découpe la grille serveur emoji par emoji', () => {
    expect(gridToCells('🟩🟨⬛🟪🟩')).toEqual(['🟩', '🟨', '⬛', '🟪', '🟩']);
    expect(gridToCells('')).toEqual([]);
    expect(gridToCells(undefined)).toEqual([]);
  });

  it('apiErrorMessage lit detail string ou liste Pydantic, sinon repli', () => {
    expect(apiErrorMessage({ detail: 'Pseudo interdit.' }, 'x')).toBe('Pseudo interdit.');
    expect(apiErrorMessage({ detail: [{ loc: ['body', 'pseudo'], msg: 'trop long' }] }, 'x')).toBe('trop long');
    expect(apiErrorMessage({}, 'Repli')).toBe('Repli');
    expect(apiErrorMessage(null, 'Repli')).toBe('Repli');
  });
});

/* ------------------------------------------------------------------ */
/* MR-08 — Rappel quotidien (Web Push)                                 */
/* ------------------------------------------------------------------ */
import {
  countCompletedDailies, pushOptinEligible, getPushPref, setPushPref, PUSH_PREF_KEY,
  urlBase64ToUint8Array, pushSupported, pushSettingLabel,
} from './dailyStore.js';

describe('MR-08 push helpers', () => {
  it('countCompletedDailies compte seulement les snapshots mr:daily:* complétés', () => {
    const st = memStorage({
      'mr:daily:2026-09-10:all': JSON.stringify({ completed: true, cells: ['🟩'] }),
      'mr:daily:2026-09-11:all': JSON.stringify({ completed: false, cells: ['🟩'] }),
      'mr:daily:2026-09-12:cat:3': JSON.stringify({ completed: true }),
      'mr:daily:2026-09-09:all': 'pas du json',
      'mr:streak': JSON.stringify({ currentStreak: 3 }),
    });
    expect(countCompletedDailies(st)).toBe(2);
    expect(countCompletedDailies(memStorage())).toBe(0);
    expect(countCompletedDailies(null)).toBe(0);
  });

  it("pushOptinEligible : jamais à la première partie, oui à partir de la 2e", () => {
    expect(pushOptinEligible(0)).toBe(false);
    expect(pushOptinEligible(1)).toBe(false);
    expect(pushOptinEligible(2)).toBe(true);
    expect(pushOptinEligible('5')).toBe(true);
  });

  it('getPushPref / setPushPref persistent le réglage', () => {
    const st = memStorage();
    expect(getPushPref(st)).toEqual({ enabled: false, endpoint: null, tz: null, everAsked: false });
    setPushPref({ enabled: true, endpoint: 'https://push.example/1', tz: 'America/Toronto' }, st);
    expect(JSON.parse(st.getItem(PUSH_PREF_KEY)).enabled).toBe(true);
    expect(getPushPref(st).tz).toBe('America/Toronto');
    setPushPref({ enabled: false }, st);
    expect(getPushPref(st)).toMatchObject({ enabled: false, endpoint: 'https://push.example/1' });
    st.setItem(PUSH_PREF_KEY, '{oops');
    expect(getPushPref(st).enabled).toBe(false);
  });

  it('urlBase64ToUint8Array décode une clé VAPID base64url (65 octets, préfixe 0x04)', () => {
    const key = 'BKrPi8s6u7dnqEpi8ku1nDOQk89AAPb2zZnxI0INXoO51QktC-p7Wos9jGUg8PawCrki_mBB6N4586VwsvQKiJs';
    const bytes = urlBase64ToUint8Array(key);
    expect(bytes).toBeInstanceOf(Uint8Array);
    expect(bytes.length).toBe(65);
    expect(bytes[0]).toBe(0x04);
    expect(urlBase64ToUint8Array('AQID').length).toBe(3);
  });

  it('pushSupported exige Notification + PushManager + serviceWorker', () => {
    const nav = { serviceWorker: {} };
    expect(pushSupported({ Notification: {}, PushManager: {}, isSecureContext: true }, nav)).toBe(true);
    expect(pushSupported({ Notification: {}, isSecureContext: true }, nav)).toBe(false); // iOS Safari non installé
    expect(pushSupported({ Notification: {}, PushManager: {} }, {})).toBe(false);
    expect(pushSupported(null, null)).toBe(false);
  });

  it('pushSettingLabel', () => {
    expect(pushSettingLabel(true)).toBe('Rappel quotidien : activé');
    expect(pushSettingLabel(false)).toBe('Rappel quotidien : désactivé');
  });
});
