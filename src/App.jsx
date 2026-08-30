import React, { useState } from 'react';
import { GameEngine } from './services/gameService.js';
import ScoreBoard from './components/ScoreBoard.jsx';
import QuoteCard from './components/QuoteCard.jsx';
import HintSystem from './components/HintSystem.jsx';
import AnswerForm from './components/AnswerForm.jsx';
import GameControls from './components/GameControls.jsx';

const game = new GameEngine();

export const App = () => {
  const [quote, setQuote] = useState(game.currentQuote);
  const [score, setScore] = useState(game.score);
  const [streak, setStreak] = useState(game.streak);
  const [highScore, setHighScore] = useState(game.highScore);
  const [revealedHints, setRevealedHints] = useState(new Set());
  const [isRevealed, setIsRevealed] = useState(false);
  const [toast, setToast] = useState(null);

  const showNotification = (msg, success = true) => {
    setToast({ msg, success });
    setTimeout(() => setToast(null), 3000);
  };

  const handleRevealHint = (type) => {
    const res = game.revealHint(type);
    if (res.success) {
      setRevealedHints(new Set(game.revealedHints));
      showNotification(`Indice débloqué: ${type.toUpperCase()}`, true);
    } else {
      showNotification(res.reason, false);
    }
  };

  const handleSubmitAnswer = (artistInput, titleInput) => {
    const res = game.validateAnswer(artistInput, titleInput);
    setScore(game.score);
    setStreak(game.streak);
    setHighScore(game.highScore);

    if (res.success) {
      showNotification(`${res.message} (+${res.pointsGained} pts)`, true);
      if (res.isFullyGuessed) {
        setIsRevealed(true);
      }
    } else {
      showNotification(res.message, false);
    }
  };

  const handleNextQuote = () => {
    setIsRevealed(true);
    setTimeout(() => {
      const newQuote = game.selectRandomQuote();
      setQuote(newQuote);
      setRevealedHints(new Set());
      setIsRevealed(false);
      setStreak(game.streak);
    }, 800);
  };

  const handleResetGame = () => {
    game.resetGame();
    setQuote(game.currentQuote);
    setScore(0);
    setStreak(0);
    setRevealedHints(new Set());
    setIsRevealed(false);
    showNotification('Partie réinitialisée !', true);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8 flex flex-col justify-between font-sans">
      <ScoreBoard score={score} streak={streak} highScore={highScore} />

      <main className="max-w-4xl mx-auto w-full flex-grow flex flex-col justify-center space-y-6">
        {toast && (
          <div className={`p-4 rounded-xl text-center font-semibold text-xs shadow-lg transition ${
            toast.success ? 'bg-emerald-900/90 text-emerald-200 border border-emerald-500' : 'bg-rose-950/90 text-rose-200 border border-rose-500'
          }`}>
            {toast.msg}
          </div>
        )}

        <div className="bg-slate-900/80 rounded-3xl p-6 md:p-8 shadow-2xl space-y-4 border border-white/10">
          <QuoteCard
            quote={quote}
            progressText={`${game.playedIds.size} / ${game.quotes.length}`}
            isRevealed={isRevealed}
            artist={quote?.artist}
            title={quote?.title}
          />

          <HintSystem
            hints={quote?.hints}
            revealedHints={revealedHints}
            onRevealHint={handleRevealHint}
          />

          <AnswerForm
            onSubmitAnswer={handleSubmitAnswer}
            artistGuessed={game.artistGuessed}
            titleGuessed={game.titleGuessed}
            isFullyGuessed={isRevealed}
          />

          <GameControls
            onNextQuote={handleNextQuote}
            onResetGame={handleResetGame}
          />
        </div>
      </main>

      <footer className="max-w-4xl mx-auto w-full mt-8 text-center text-xs text-slate-500">
        <p>Music Refs v1.0.0 — ADA Task #4 Feature Branch <code className="text-purple-400">ada-feature-4</code></p>
      </footer>
    </div>
  );
};

export default App;
