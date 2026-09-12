import { MUSIC_QUOTES } from '../data/quotes.js';

const STORAGE_KEY_SCORE = 'music_refs_high_score';
const STORAGE_KEY_STATS = 'music_refs_stats';

/**
 * Load quotes from API; fall back to static MUSIC_QUOTES if unavailable.
 */
export async function loadQuotesFromApi(apiBase = '', categoryId = null) {
  try {
    const qs = categoryId != null ? `?category_id=${encodeURIComponent(categoryId)}` : '';
    const res = await fetch(`${apiBase}/api/music-refs/quotes${qs}`, {
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (Array.isArray(data) && data.length > 0) {
      return data;
    }
  } catch (err) {
    console.warn('Music Refs API unavailable, using static quotes:', err);
  }
  return MUSIC_QUOTES;
}

export async function loadCategories(apiBase = '') {
  const res = await fetch(`${apiBase}/api/music-refs/categories`, {
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/**
 * SEC-01 — Propositions du mode quiz calculées côté serveur (bonne réponse + distracteurs,
 * mélangés, sans indiquer laquelle est bonne). Repli local si la punchline porte encore
 * ses réponses (catalogue statique hors-ligne).
 */
export async function loadQuizOptions(apiBase = '', quote, pool = [], { count = 4, categoryId = null } = {}) {
  if (!quote) return { artists: [], titles: [] };
  if (quote.artist && quote.title) {
    return buildQuizChoices(quote, pool, count);
  }
  const params = new URLSearchParams({ count: String(count) });
  if (categoryId != null) params.set('category_id', String(categoryId));
  const res = await fetch(`${apiBase}/api/music-refs/quotes/${encodeURIComponent(quote.id)}/options?${params}`, {
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/**
 * SEC-02 — Verdict serveur pour le mode solo (MR-11).
 * @returns {Promise<{artist_ok:boolean,title_ok:boolean,fully_correct:boolean,points:number,message?:string,reveal?:object}>}
 */
export async function submitSoloAnswer(apiBase = '', quoteId, { artist = '', title = '', hintsUsed = 0, mode = 'classic' } = {}) {
  const res = await fetch(`${apiBase}/api/music-refs/quotes/${encodeURIComponent(quoteId)}/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ artist, title, hints_used: hintsUsed, mode }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : `HTTP ${res.status}`);
  }
  return data;
}

/** Abandon (« Passer ») : révèle la réponse d'une punchline. */
export async function revealSoloQuote(apiBase = '', quoteId) {
  const res = await fetch(`${apiBase}/api/music-refs/quotes/${encodeURIComponent(quoteId)}/reveal`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/**
 * Build multiple-choice options for easy/quiz mode.
 * Returns { artists: string[], titles: string[] } (correct answer included, shuffled).
 */
export function buildQuizChoices(currentQuote, pool, count = 4) {
  if (!currentQuote) return { artists: [], titles: [] };
  const others = (pool || []).filter((q) => q && q.id !== currentQuote.id);

  function pickField(field, correct) {
    const uniq = new Set();
    const correctNorm = normalizeString(correct);
    const options = [correct];
    uniq.add(correctNorm);
    const shuffled = [...others].sort(() => Math.random() - 0.5);
    for (const q of shuffled) {
      const val = (q[field] || '').trim();
      if (!val) continue;
      const n = normalizeString(val);
      if (uniq.has(n)) continue;
      uniq.add(n);
      options.push(val);
      if (options.length >= count) break;
    }
    // Pad with generic distractors if pool too small
    const fillers = field === 'artist'
      ? ['Artiste Mystère', 'Inconnu·e', 'Anonymous', 'DJ X']
      : ['Sans titre', 'Track #1', 'Bonus', 'Interlude'];
    for (const f of fillers) {
      if (options.length >= count) break;
      const n = normalizeString(f);
      if (uniq.has(n)) continue;
      uniq.add(n);
      options.push(f);
    }
    return options.sort(() => Math.random() - 0.5);
  }

  return {
    artists: pickField('artist', currentQuote.artist),
    titles: pickField('title', currentQuote.title),
  };
}

/** Strip leading articles (FR/EN) before normalize — « Le Titre » ↔ « Titre ». */
export function stripLeadingArticles(str) {
  if (!str) return '';
  let out = String(str).trim();
  let prev;
  do {
    prev = out;
    out = out.replace(/^(l'|d'|l’|d’)/i, '').replace(/^(le|la|les|un|une|des|du|de|the|a|an|à)\s+/i, '').trim();
  } while (out !== prev);
  return out;
}

/**
 * Strips accents, punctuation, and converts string to lower-case for flexible comparison.
 */
export function normalizeString(str) {
  if (!str) return '';
  return stripLeadingArticles(str)
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // remove diacritics
    .replace(/[^a-z0-9]/g, '') // remove non-alphanumeric
    .trim();
}

/** Tokenize keeping word boundaries (for Matt / M. / Pokora). */
export function tokenizeName(str) {
  if (!str) return [];
  return stripLeadingArticles(str)
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[''`]/g, '')
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
}

/**
 * Known aliases (any form ↔ any form). Keep compact normalized keys.
 * Extend freely for stage names / orthographe courante.
 */
const ALIAS_GROUPS = [
  ['mpokora', 'mattpokora', 'matthieupokora'],
  ['gims', 'maitregims'],
  ['sexiondassaut', 'sexiondassault'],
  ['belkatobis', 'belkatobbi', 'belkatobi'],
];

function aliasKeys(compact) {
  const keys = new Set([compact]);
  for (const group of ALIAS_GROUPS) {
    if (group.includes(compact)) {
      group.forEach((k) => keys.add(k));
    }
  }
  return keys;
}

function firstNamesCompatible(a, b) {
  if (!a || !b) return true;
  if (a === b) return true;
  // Initial : M. ↔ Matt, J. ↔ Jean
  if (a.length === 1 && b.startsWith(a)) return true;
  if (b.length === 1 && a.startsWith(b)) return true;
  // Préfixe : Matt ↔ Matthew
  if (a.length >= 3 && b.length >= 3 && (a.startsWith(b) || b.startsWith(a))) return true;
  return levenshteinDistance(a, b) <= 1;
}

/**
 * Flexible match: exact, substring, aliases, initiales (M. Pokora ↔ Matt Pokora), typos.
 */
export function isMatch(input, target) {
  const normInput = normalizeString(input);
  const normTarget = normalizeString(target);
  if (!normInput || !normTarget) return false;

  if (normInput === normTarget) return true;

  // Alias groups (Matt Pokora ↔ M. Pokora, etc.)
  const inAliases = aliasKeys(normInput);
  const tgAliases = aliasKeys(normTarget);
  for (const a of inAliases) {
    if (tgAliases.has(a)) return true;
  }

  // Substring if input length >= 3
  if (normInput.length >= 3) {
    if (normTarget.includes(normInput) || normInput.includes(normTarget)) {
      return true;
    }
  }

  // Token logic: "M. Pokora" ↔ "Matt Pokora", "Pokora" seul si assez long
  const tIn = tokenizeName(input);
  const tTg = tokenizeName(target);
  if (tIn.length && tTg.length) {
    const lastIn = tIn[tIn.length - 1];
    const lastTg = tTg[tTg.length - 1];
    if (lastIn.length >= 4 && lastIn === lastTg) {
      if (tIn.length === 1 || tTg.length === 1) return true; // nom seul
      if (firstNamesCompatible(tIn[0], tTg[0])) return true;
    }
    // Tous les tokens de la saisie (courte) présents dans la cible
    if (tIn.length <= tTg.length && tIn.every((tok) => tTg.some((x) => x === tok || (tok.length === 1 && x.startsWith(tok)) || (tok.length >= 3 && x.startsWith(tok))))) {
      return true;
    }
  }

  // Levenshtein ≤2 si cible ≥6 lettres, sinon ≤1
  const dist = levenshteinDistance(normInput, normTarget);
  const maxAllowed = normTarget.length >= 6 ? 2 : 1;
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

/**
 * Barème local (uniquement pour le repli hors-ligne sur le catalogue statique) —
 * identique au barème serveur (backend/scoring.py).
 */
export function localVerdict(quote, inputArtist, inputTitle, hintsUsed = 0) {
  const artist = (inputArtist || '').trim();
  const title = (inputTitle || '').trim();
  let artistOk = artist ? isMatch(artist, quote.artist) : false;
  let titleOk = title ? isMatch(title, quote.title) : false;
  if (artist && !title && isMatch(artist, quote.title)) titleOk = true;
  if (title && !artist && isMatch(title, quote.artist)) artistOk = true;
  let points = 0;
  if (artistOk) points += 100;
  if (titleOk) points += 100;
  if (artistOk && titleOk) points += 50;
  if (points > 0) {
    points = Math.max(20, points - Math.min(hintsUsed, 4) * 20);
  }
  const fully = artistOk && titleOk;
  return {
    artist_ok: artistOk,
    title_ok: titleOk,
    fully_correct: fully,
    half_points: artistOk && !titleOk,
    points,
    message: fully
      ? `Artiste trouvé: ${quote.artist} | Titre trouvé: ${quote.title}`
      : artistOk
        ? `Artiste juste (${quote.artist}), titre faux : moitié des points.`
        : titleOk
          ? `Titre trouvé: ${quote.title} — il manque l'artiste.`
          : 'Mauvaise réponse. Réessayez ou demandez un indice !',
    reveal: fully ? { artist: quote.artist, title: quote.title, listen_url: quote.listen_url || '' } : null,
  };
}

export class GameEngine {
  /**
   * @param {Array} quotesList
   * @param {object} [opts]
   * @param {(quote:object, payload:{artist:string,title:string,hintsUsed:number}) => Promise<object>} [opts.verify]
   *   Vérificateur serveur (SEC-02/SEC-03). Sans lui, repli local si la punchline porte ses réponses.
   * @param {boolean} [opts.comboBonus=true] bonus de série calculé localement ((série-1)×50) ;
   *   false quand le serveur l'inclut déjà (salon).
   */
  constructor(quotesList = MUSIC_QUOTES, opts = {}) {
    this.verify = typeof opts.verify === 'function' ? opts.verify : null;
    this.comboBonus = opts.comboBonus !== false;
    this.quotes = [...quotesList];
    this.quotePoints = 0; // points déjà attribués pour la punchline courante (total cumulé serveur)
    this.acceptedArtist = '';
    this.acceptedTitle = '';
    this.reveal = null; // {artist, title, listen_url} une fois connu (verdict complet ou abandon)
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
    this.orderedMode = false;
    this.orderIndex = 0;

    if (this.quotes.length > 0) {
      this.selectRandomQuote();
    }
  }

  /**
   * Replace quote pool (e.g. after API load) and pick a fresh quote.
   * @param {object} [opts]
   * @param {boolean} [opts.ordered] play in list order (party mode)
   */
  setVerifier(fn) {
    this.verify = typeof fn === 'function' ? fn : null;
  }

  /** Réinitialise l'état propre à une punchline. */
  _resetQuoteState() {
    this.revealedHints.clear();
    this.artistGuessed = false;
    this.titleGuessed = false;
    this.quotePoints = 0;
    this.acceptedArtist = '';
    this.acceptedTitle = '';
    this.reveal = null;
  }

  setQuotes(quotesList, opts = {}) {
    this.quotes = Array.isArray(quotesList) && quotesList.length ? [...quotesList] : [...MUSIC_QUOTES];
    this.playedIds.clear();
    this.orderedMode = !!opts.ordered;
    this.orderIndex = 0;
    if (this.orderedMode) {
      return this.selectOrderedQuote(0);
    }
    this.selectRandomQuote();
    return this.currentQuote;
  }

  selectOrderedQuote(index = 0) {
    this._resetQuoteState();
    if (!this.quotes.length) {
      this.currentQuote = null;
      return null;
    }
    this.orderIndex = Math.max(0, Math.min(index, this.quotes.length - 1));
    this.currentQuote = this.quotes[this.orderIndex];
    this.playedIds.add(this.currentQuote.id);
    return this.currentQuote;
  }

  /**
   * Next quote in party order. Returns null when finished.
   */
  advanceOrdered() {
    if (!this.orderedMode) {
      return this.selectRandomQuote();
    }
    if (this.orderIndex >= this.quotes.length - 1) {
      return null;
    }
    return this.selectOrderedQuote(this.orderIndex + 1);
  }

  isPartyComplete() {
    return this.orderedMode && this.orderIndex >= this.quotes.length - 1
      && this.artistGuessed && this.titleGuessed;
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
    this._resetQuoteState();

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

  /**
   * Valide une réponse. Le VERDICT (artiste/titre justes, points de base) vient du
   * serveur via `this.verify` ; le moteur ne garde que combo, record et HUD.
   * Repli local uniquement si la punchline porte ses réponses (catalogue statique).
   * @returns {Promise<object>} même forme qu'avant (success, pointsGained, streak, score, …)
   */
  async validateAnswer(inputArtist, inputTitle) {
    if (!this.currentQuote) return { success: false, message: 'No active quote' };
    const q = this.currentQuote;
    // On renvoie les champs déjà validés pour que le serveur voie l'état cumulé.
    const artist = this.artistGuessed ? this.acceptedArtist : (inputArtist || '').trim();
    const title = this.titleGuessed ? this.acceptedTitle : (inputTitle || '').trim();
    if (!artist && !title) {
      return { success: false, pointsGained: 0, streak: this.streak, score: this.score, message: 'Saisissez au moins l\'artiste ou le titre.' };
    }
    const hintsUsed = this.revealedHints.size;
    let verdict;
    if (this.verify) {
      verdict = await this.verify(q, { artist, title, hintsUsed });
    } else if (q.artist && q.title) {
      verdict = localVerdict(q, artist, title, hintsUsed);
    } else {
      return { success: false, pointsGained: 0, streak: this.streak, score: this.score, message: 'Vérification indisponible (serveur injoignable).' };
    }
    return this.applyVerdict(verdict, { artist, title });
  }

  /**
   * Applique un verdict (serveur ou local) à l'état du moteur : combo, record, score.
   * `verdict.points` = total cumulé pour la punchline ; si `verdict.score` est fourni
   * (salon), il fait autorité.
   */
  applyVerdict(verdict, { artist = '', title = '' } = {}) {
    if (!verdict) return { success: false, pointsGained: 0, streak: this.streak, score: this.score, message: 'Verdict indisponible' };
    const artistMatch = !!verdict.artist_ok && !this.artistGuessed;
    const titleMatch = !!verdict.title_ok && !this.titleGuessed;
    this.totalAttempts++;

    if (verdict.reveal) this.reveal = verdict.reveal;
    if (verdict.artist_ok) {
      this.artistGuessed = true;
      if (artist) this.acceptedArtist = artist;
    }
    if (verdict.title_ok) {
      this.titleGuessed = true;
      if (title) this.acceptedTitle = title;
    }
    const isFullyGuessed = this.artistGuessed && this.titleGuessed;

    if (!artistMatch && !titleMatch) {
      if (!this.artistGuessed && !this.titleGuessed) {
        this.streak = 0; // erreur totale : la série tombe
      }
      if (Number.isFinite(verdict.streak)) this.streak = verdict.streak;
      if (Number.isFinite(verdict.score)) this.score = verdict.score;
      return {
        success: false,
        pointsGained: 0,
        streak: this.streak,
        score: this.score,
        message: verdict.message || 'Mauvaise réponse. Réessayez ou demandez un indice !'
      };
    }

    let pointsGained;
    if (Number.isFinite(verdict.score)) {
      // Score serveur (salon) : autorité totale, série incluse.
      pointsGained = Number.isFinite(verdict.awarded) ? verdict.awarded : Math.max(0, verdict.score - this.score);
      this.score = verdict.score;
      if (Number.isFinite(verdict.streak)) this.streak = verdict.streak;
      else if (isFullyGuessed) this.streak++;
    } else {
      const total = Number(verdict.points) || 0;
      pointsGained = Math.max(0, total - this.quotePoints);
      this.quotePoints = Math.max(this.quotePoints, total);
      if (isFullyGuessed) {
        this.streak++;
        if (this.comboBonus) pointsGained += (this.streak - 1) * 50; // bonus de série local
      }
      this.score += pointsGained;
    }
    if (isFullyGuessed) this.successfulQuotes++;
    this.saveHighScore(this.score);

    return {
      success: true,
      artistMatched: artistMatch,
      titleMatched: titleMatch,
      isFullyGuessed,
      halfPoints: !!verdict.half_points,
      pointsGained,
      streak: this.streak,
      score: this.score,
      highScore: this.highScore,
      reveal: this.reveal,
      message: verdict.message || 'Bonne réponse !'
    };
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
