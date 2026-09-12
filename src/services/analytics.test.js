import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  track,
  trackEvent,
  flush,
  getPlayerId,
  buildBatch,
  getQueue,
  clearQueue,
  configure,
  _resetForTests,
  EVENT_NAMES,
} from './analytics.js';

function fakeStorage() {
  const m = new Map();
  return {
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => m.set(k, String(v)),
    removeItem: (k) => m.delete(k),
    clear: () => m.clear(),
  };
}

const listeners = {};
const fakeDocument = {
  visibilityState: 'visible',
  addEventListener: (type, fn) => { listeners[type] = fn; },
};

describe('analytics.js — file d\'attente, lot, envoi (MR-19)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal('localStorage', fakeStorage());
    vi.stubGlobal('document', fakeDocument);
    vi.stubGlobal('window', { addEventListener: () => {} });
    vi.stubGlobal('navigator', { sendBeacon: vi.fn(() => true) });
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200 })));
    vi.spyOn(console, 'info').mockImplementation(() => {});
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    _resetForTests();
    clearQueue();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('réutilise l\'UUID joueur du daily (clé mr:player)', () => {
    localStorage.setItem('mr:player', JSON.stringify({ id: 'abcd-1234-efgh-5678', pseudo: 'Stef' }));
    expect(getPlayerId()).toBe('abcd-1234-efgh-5678');
  });

  it('crée un identifiant anonyme sous mr:player s\'il n\'existe pas, sans donnée personnelle', () => {
    const id = getPlayerId();
    expect(id.length).toBeGreaterThanOrEqual(8);
    const stored = JSON.parse(localStorage.getItem('mr:player'));
    expect(stored).toEqual({ id, pseudo: '' });
    expect(getPlayerId()).toBe(id); // stable
  });

  it('track enfile un événement de la liste blanche avec props nettoyées', () => {
    expect(track('daily_completed', { score: 40, hints: 1, timeMs: 61000, nested: { a: 1 }, list: [1] })).toBe(true);
    const q = getQueue();
    expect(q).toHaveLength(1);
    expect(q[0].name).toBe('daily_completed');
    expect(q[0].props).toEqual({ score: 40, hints: 1, timeMs: 61000 });
    expect(typeof q[0].ts).toBe('string');
    expect(trackEvent).toBe(track); // alias historique
  });

  it('ignore un nom hors liste blanche', () => {
    expect(track('pageview', {})).toBe(false);
    expect(getQueue()).toHaveLength(0);
    expect(EVENT_NAMES.has('share_landed')).toBe(true);
  });

  it('buildBatch produit { player_id, tz, events[≤50] }', () => {
    localStorage.setItem('mr:player', JSON.stringify({ id: 'player-000001', pseudo: '' }));
    for (let i = 0; i < 60; i++) track('daily_started', { i });
    const batch = buildBatch(getQueue());
    expect(batch.player_id).toBe('player-000001');
    expect(typeof batch.tz).toBe('string');
    expect(batch.events).toHaveLength(50);
    expect(batch.events[0]).toMatchObject({ name: 'daily_started', props: { i: 0 } });
    expect(Object.keys(batch)).toEqual(['player_id', 'tz', 'events']);
  });

  it('flush envoie via fetch keepalive en JSON et vide la file (lots de 50)', async () => {
    for (let i = 0; i < 60; i++) track('share_clicked', { channel: 'whatsapp' });
    expect(await flush()).toBe(true);
    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, opts] = fetch.mock.calls[0];
    expect(url).toBe('/api/music-refs/events');
    expect(opts.method).toBe('POST');
    expect(opts.keepalive).toBe(true);
    expect(opts.headers['Content-Type']).toBe('application/json');
    const body = JSON.parse(opts.body);
    expect(body.events).toHaveLength(50);
    expect(body.events[0]).toMatchObject({ name: 'share_clicked', props: { channel: 'whatsapp' } });
    expect(getQueue()).toHaveLength(10);
  });

  it('flush remet le lot en file si le réseau échoue ou si le serveur répond 5xx', async () => {
    fetch.mockRejectedValueOnce(new Error('offline'));
    track('notif_optin');
    expect(await flush()).toBe(false);
    expect(getQueue()).toHaveLength(1);
    fetch.mockResolvedValueOnce({ ok: false, status: 503 });
    expect(await flush()).toBe(false);
    expect(getQueue()).toHaveLength(1);
    fetch.mockResolvedValueOnce({ ok: false, status: 422 }); // refus définitif : on ne boucle pas
    expect(await flush()).toBe(true);
    expect(getQueue()).toHaveLength(0);
  });

  it('flush({ beacon: true }) utilise navigator.sendBeacon, et remet en file si refusé', async () => {
    track('quote_submitted');
    expect(await flush({ beacon: true })).toBe(true);
    expect(navigator.sendBeacon).toHaveBeenCalledTimes(1);
    expect(navigator.sendBeacon.mock.calls[0][0]).toBe('/api/music-refs/events');
    expect(fetch).not.toHaveBeenCalled();
    expect(getQueue()).toHaveLength(0);

    navigator.sendBeacon.mockReturnValueOnce(false);
    track('challenge_created');
    expect(await flush({ beacon: true })).toBe(false);
    expect(getQueue()).toHaveLength(1);
  });

  it('vidage périodique : le timer déclenche fetch après flushIntervalMs', async () => {
    configure({ flushIntervalMs: 5000 });
    track('streak_milestone', { days: 7 });
    expect(fetch).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(5000);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(getQueue()).toHaveLength(0);
  });

  it('vidage au visibilitychange (page cachée) via sendBeacon', () => {
    track('challenge_accepted');
    fakeDocument.visibilityState = 'hidden';
    listeners.visibilitychange();
    fakeDocument.visibilityState = 'visible';
    expect(navigator.sendBeacon).toHaveBeenCalledTimes(1);
    expect(getQueue()).toHaveLength(0);
  });

  it('appelle window.plausible si présent (hook conservé)', () => {
    const plausible = vi.fn();
    vi.stubGlobal('window', { addEventListener: () => {}, plausible });
    track('daily_started', { edition: 3 });
    expect(plausible).toHaveBeenCalledWith('daily_started', { props: { edition: 3 } });
  });
});
