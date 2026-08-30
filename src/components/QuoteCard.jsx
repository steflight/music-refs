import React from 'react';

export const QuoteCard = ({ quote, progressText, isRevealed, artist, title }) => {
  if (!quote) return null;

  return (
    <div className="bg-slate-900/80 backdrop-blur-md rounded-3xl p-6 md:p-8 shadow-2xl relative overflow-hidden border border-white/10">
      <div className="flex justify-between items-center text-xs text-slate-400 mb-4">
        <span className="bg-purple-900/60 text-purple-300 font-bold px-3 py-1 rounded-full border border-purple-500/30 uppercase">
          🎵 Citation #{quote.id}
        </span>
        <span>Progression : <strong className="text-white">{progressText}</strong></span>
      </div>

      <div className="bg-slate-950/70 p-6 md:p-8 rounded-2xl border border-white/10 relative my-4">
        <p className="text-xl md:text-2xl font-bold text-white text-center leading-relaxed italic">
          “{quote.quote}”
        </p>
      </div>

      {isRevealed && (
        <div className="bg-emerald-950/80 border border-emerald-500/50 p-4 rounded-xl text-center space-y-1 my-3">
          <p className="text-xs uppercase font-bold text-emerald-400">Réponse Découverte</p>
          <p className="text-lg font-extrabold text-white">
            <span className="text-cyan-400">{artist}</span> — <span className="text-pink-400">{title}</span>
          </p>
        </div>
      )}
    </div>
  );
};
export default QuoteCard;
