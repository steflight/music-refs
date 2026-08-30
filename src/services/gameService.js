import { MUSIC_QUOTES } from '../data/quotes.js';

const STORAGE_KEY_SCORE = 'music_refs_high_score';
const STORAGE_KEY_STATS = 'music_refs_stats';

/**
 * Strips accents, punctuation, and converts string to lower-case for flexible comparison.
 */
export function normalizeString(str) {
  if (!str) return '';
  return str
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // remove diacritics
    .replace(/[^a-z0-9]/g, '') // remove non-alphanumeric
    .trim();
}

/**
 * Calculates simple similarity or substring match between user input and target answer.
 */
export function isMatch(input, target) {
  const normInput = normalizeString(input);
  const normTarget = normalizeString(target);
  if (!normInput || !normTarget) return false;

  if (normInput === normTarget) return true;

  // Allow partial match if input length >= 3 and is contained or close
  if (normInput.length >= 3) {
    if (normTarget.includes(normInput) || normInput.includes(normTarget)) {
      return true;
    }
  }

  // Levenshtein distance for fuzzy matching (allows 1 typo for short words, 2 for long)
  const dist = levenshteinDistance(normInput, normTarget);
  const maxAllowed = normTarget.length > 6 ? 2 : 1;
  return dist <= maxAllowed;
}

function levenshteinDistance(a, b) {
  const matrix = Array.from({ length: a.length + 1 }, () => Array(b.length + 1).fill(0));
  for (let i = 0; i <= a.length; i++) matrix[i][0] = i;
  for (let j = 0; j <= b.length; j++) matrix[0][j] = j;

  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      matrix[i][j] = Math.min(
        matrix[i - 1][j] + 1,
        matrix[i][j - 1] + 1,
        matrix[i - 1][j - 1] + cost
      );
    }
  }
  return matrix[a.length][b.length];
}

export class GameEngine {
  constructor(quotesList = MUSIC_QUOTES) {
    this.quotes = [...quotesList];
    this.playedIds = new Set();
    this.currentQuote = null;
    this.score = 0;
    this.streak = 0;
    this.highScore = this.getStoredHighScore();
    this.revealedHints = new Set(); // e.g. 'year', 'genre', 'album', 'initials'
    this.artistGuessed = false;
    this.titleGuessed = false;
    this.totalAttempts = 0;
    this.successfulQuotes = 0;

    this.selectRandomQuote();
  }

  getStoredHighScore() {
    try {
      const val = localStorage.getItem(STORAGE_KEY_SCORE);
      return val ? parseInt(val, 10) : 0;
    } catch (e) {
      return 0;
    }
  }

  saveHighScore(score) {
    try {
      if (score > this.highScore) {
        this.highScore = score;
        localStorage.setItem(STORAGE_KEY_SCORE, score.toString());
      }
    } catch (e) {
      console.warn('localStorage disabled');
    }
  }

  selectRandomQuote() {
    // Reset quote state
    this.revealedHints.clear();
    this.artistGuessed = false;
    this.titleGuessed = false;

    // Reset played if all have been played
    if (this.playedIds.size >= this.quotes.length) {
      this.playedIds.clear();
    }

    const available = this.quotes.filter(q => !this.playedIds.has(q.id));
    if (available.length === 0) {
      this.currentQuote = this.quotes[0];
      return this.currentQuote;
    }

    const randomIndex = Math.floor(Math.random() * available.length);
    this.currentQuote = available[randomIndex];
    this.playedIds.add(this.currentQuote.id);
    return this.currentQuote;
  }

  revealHint(hintType) {
    if (!this.currentQuote || !this.currentQuote.hints[hintType]) {
      return { success: false, reason: 'Hint not available' };
    }

    if (this.revealedHints.has(hintType)) {
      return { success: false, reason: 'Hint already revealed' };
    }

    this.revealedHints.add(hintType);
    return {
      success: true,
      hintType,
      value: this.currentQuote.hints[hintType],
      revealedCount: this.revealedHints.size
    };
  }

  validateAnswer(inputArtist, inputTitle) {
    if (!this.currentQuote) return { success: false, message: 'No active quote' };

    let artistMatch = false;
    let titleMatch = false;

    if (inputArtist && !this.artistGuessed) {
      artistMatch = isMatch(inputArtist, this.currentQuote.artist);
    }
    if (inputTitle && !this.titleGuessed) {
      titleMatch = isMatch(inputTitle, this.currentQuote.title);
    }

    // Also support single input field guessing either or both
    if (!inputTitle && inputArtist) {
      if (!this.artistGuessed && isMatch(inputArtist, this.currentQuote.artist)) {
        artistMatch = true;
      }
      if (!this.titleGuessed && isMatch(inputArtist, this.currentQuote.title)) {
        titleMatch = true;
      }
    }

    this.totalAttempts++;

    let pointsGained = 0;
    let feedback = [];

    if (artistMatch && !this.artistGuessed) {
      this.artistGuessed = true;
      pointsGained += 100;
      feedback.push(`Artiste trouvé: ${this.currentQuote.artist}`);
    }

    if (titleMatch && !this.titleGuessed) {
      this.titleGuessed = true;
      pointsGained += 100;
      feedback.push(`Titre trouvé: ${this.currentQuote.title}`);
    }

    const isFullyGuessed = this.artistGuessed && this.titleGuessed;

    if (pointsGained > 0) {
      // Calculate hint penalties (-20 per hint used)
      const hintPenalty = this.revealedHints.size * 20;
      pointsGained = Math.max(20, pointsGained - hintPenalty);

      // Streak bonus if full quote guessed
      if (isFullyGuessed) {
        this.streak++;
        this.successfulQuotes++;
        const streakBonus = (this.streak - 1) * 50;
        pointsGained += 50 + streakBonus; // full guess bonus + streak multiplier
      }

      this.score += pointsGained;
      this.saveHighScore(this.score);

      return {
        success: true,
        artistMatched: artistMatch,
        titleMatched: titleMatch,
        isFullyGuessed,
        pointsGained,
        streak: this.streak,
        score: this.score,
        highScore: this.highScore,
        message: feedback.join(' | ') || 'Bonne réponse !'
      };
    } else {
      // Wrong guess
      if (!this.artistGuessed && !this.titleGuessed) {
        this.streak = 0; // reset streak on total error
      }
      return {
        success: false,
        pointsGained: 0,
        streak: this.streak,
        score: this.score,
        message: 'Mauvaise réponse. Réessayez ou demandez un indice !'
      };
    }
  }

  skipQuote() {
    this.streak = 0;
    const previousQuote = this.currentQuote;
    const nextQuote = this.selectRandomQuote();
    return {
      previousQuote,
      nextQuote,
      score: this.score,
      streak: this.streak
    };
  }

  resetGame() {
    this.score = 0;
    this.streak = 0;
    this.playedIds.clear();
    this.totalAttempts = 0;
    this.successfulQuotes = 0;
    this.selectRandomQuote();
    return {
      score: this.score,
      streak: this.streak,
      highScore: this.highScore,
      quote: this.currentQuote
    };
  }
}
