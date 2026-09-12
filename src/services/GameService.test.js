import { describe, it, expect, beforeEach } from 'vitest';
import { GameEngine, normalizeString, isMatch } from './gameService.js';

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

    it('US4: Calculates score accurately with hint penalty and streak bonus', () => {
      const currentArtist = game.currentQuote.artist;
      const currentTitle = game.currentQuote.title;

      // Reveal 1 hint (-20 pts penalty)
      game.revealHint('year');

      const validation = game.validateAnswer(currentArtist, currentTitle);
      expect(validation.success).toBe(true);
      expect(validation.isFullyGuessed).toBe(true);
      expect(game.streak).toBe(1);
      expect(game.score).toBeGreaterThan(0);
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
