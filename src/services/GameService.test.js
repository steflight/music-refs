import { describe, it, expect, beforeEach } from 'vitest';
import { GameEngine, normalizeString, isMatch, localVerdict } from './gameService.js';

describe('GameService & String Matching Engine', () => {
  it('US2: Normalizes strings correctly removing accents and punctuation', () => {
    // MR-11 : les articles initiaux (« A l' », « Le », « The »…) sont ignorés.
    expect(normalizeString("A l'ammoniaque!")).toBe("ammoniaque");
    expect(normalizeString("À l'ammoniaque")).toBe("ammoniaque");
    expect(normalizeString("  Ninho-- ")).toBe("ninho");
    expect(normalizeString("Été indien")).toBe("eteindien");
  });

  it('US2: Correctly matches exact and fuzzy artist and title inputs', () => {
    expect(isMatch('Ninho', 'Ninho')).toBe(true);
    expect(isMatch('ninho', 'Ninho')).toBe(true);
    expect(isMatch('daft punk', 'Daft Punk')).toBe(true);
    expect(isMatch('orelsan', 'OrelSan')).toBe(true);
    expect(isMatch('pnl', 'PNL')).toBe(true);
  });

  describe('GameEngine Integration', () => {
    let game;
    const testQuotes = [
      {
        id: 101,
        quote: "Test quote 1",
        artist: "Artist One",
        title: "Song One",
        hints: { year: "2020", genre: "Pop", album: "Album One", initials: "A.O - S.O" }
      },
      {
        id: 102,
        quote: "Test quote 2",
        artist: "Artist Two",
        title: "Song Two",
        hints: { year: "2022", genre: "Rock", album: "Album Two", initials: "A.T - S.T" }
      }
    ];

    beforeEach(() => {
      game = new GameEngine(testQuotes);
    });

    it('US1: Selects random quotes without immediate repetition', () => {
      expect(game.currentQuote).toBeDefined();
      expect(testQuotes.map(q => q.id)).toContain(game.currentQuote.id);
    });

    it('US3: System d\'affichage d\'indices reveals hints and tracks count', () => {
      const res = game.revealHint('year');
      expect(res.success).toBe(true);
      expect(res.value).toBe(game.currentQuote.hints.year);
      expect(game.revealedHints.has('year')).toBe(true);

      // Attempting same hint twice fails
      const duplicateRes = game.revealHint('year');
      expect(duplicateRes.success).toBe(false);
    });

    it('US4: Calculates score accurately with hint penalty and streak bonus (repli local)', async () => {
      const currentArtist = game.currentQuote.artist;
      const currentTitle = game.currentQuote.title;

      // Reveal 1 hint (-20 pts penalty)
      game.revealHint('year');

      const validation = await game.validateAnswer(currentArtist, currentTitle);
      expect(validation.success).toBe(true);
      expect(validation.isFullyGuessed).toBe(true);
      expect(game.streak).toBe(1);
      expect(game.score).toBe(230); // 100 + 100 + 50 − 20 (1 indice)
    });

    it('SEC-02: le verdict vient du vérificateur serveur, le moteur garde combo/record', async () => {
      const calls = [];
      const verify = async (quote, payload) => {
        calls.push({ id: quote.id, ...payload });
        // 1er appel : artiste seul juste (moitié) ; 2e : complet (total cumulé 250)
        if (calls.length === 1) {
          return { artist_ok: true, title_ok: false, fully_correct: false, half_points: true, points: 100, message: 'moitié' };
        }
        return { artist_ok: true, title_ok: true, fully_correct: true, points: 250, reveal: { artist: 'Artist One', title: 'Song One' } };
      };
      // Punchlines SANS artiste/titre (vue publique SEC-01)
      const publicQuotes = testQuotes.map(({ artist, title, ...rest }) => rest);
      const g = new GameEngine(publicQuotes, { verify });

      const r1 = await g.validateAnswer('artist one', '');
      expect(r1.success).toBe(true);
      expect(r1.halfPoints).toBe(true);
      expect(r1.pointsGained).toBe(100);
      expect(g.artistGuessed).toBe(true);
      expect(g.streak).toBe(0);

      const r2 = await g.validateAnswer('', 'song one');
      expect(calls[1].artist).toBe('artist one'); // artiste déjà validé renvoyé au serveur
      expect(calls[1].title).toBe('song one');
      expect(r2.isFullyGuessed).toBe(true);
      expect(r2.pointsGained).toBe(150); // delta 250 − 100, série 1 → pas de bonus combo
      expect(g.score).toBe(250);
      expect(g.streak).toBe(1);
      expect(g.reveal).toEqual({ artist: 'Artist One', title: 'Song One' });

      // Mauvaise réponse totale sur la suivante : série remise à zéro
      g.selectRandomQuote();
      const r3 = await g.applyVerdict({ artist_ok: false, title_ok: false, fully_correct: false, points: 0 });
      expect(r3.success).toBe(false);
      expect(g.streak).toBe(0);
    });

    it('SEC-03: score serveur du salon fait autorité (score/streak/awarded)', () => {
      const g = new GameEngine([{ id: 7, quote: 'x', hints: {} }], { comboBonus: false });
      g.score = 0;
      const r = g.applyVerdict({ artist_ok: true, title_ok: true, fully_correct: true, points: 250, awarded: 300, score: 300, streak: 2 });
      expect(r.success).toBe(true);
      expect(r.pointsGained).toBe(300);
      expect(g.score).toBe(300);
      expect(g.streak).toBe(2);
    });

    it('MR-11: barème local — artiste juste, titre faux = moitié des points', () => {
      const v = localVerdict(testQuotes[0], 'Artist One', 'mauvais titre');
      expect(v.artist_ok).toBe(true);
      expect(v.title_ok).toBe(false);
      expect(v.half_points).toBe(true);
      expect(v.points).toBe(100);
      expect(localVerdict(testQuotes[0], 'Artist One', 'Song One').points).toBe(250);
    });

    it('Sans vérificateur ni réponses locales, la validation échoue proprement', async () => {
      const g = new GameEngine([{ id: 9, quote: 'x', hints: {} }]);
      const r = await g.validateAnswer('a', 'b');
      expect(r.success).toBe(false);
      expect(r.message).toMatch(/indisponible/);
    });

    it('US5: Skip quote resets streak and selects next quote', () => {
      game.streak = 3;
      const skipRes = game.skipQuote();
      expect(game.streak).toBe(0);
      expect(skipRes.nextQuote).toBeDefined();
    });

    it('US5: Reset game resets score, streak, and played history', () => {
      game.score = 500;
      game.streak = 4;
      game.resetGame();

      expect(game.score).toBe(0);
      expect(game.streak).toBe(0);
    });
  });
});
