import React from 'react';

export const GameControls = ({ onNextQuote, onResetGame }) => {
  return (
    <div className="flex flex-col sm:flex-row items-center justify-between pt-4 border-t border-white/10 gap-3">
      <button
        type="button"
        onClick={onNextQuote}
        className="w-full sm:w-auto bg-white/10 hover:bg-white/20 text-white font-semibold text-xs py-2.5 px-5 rounded-xl transition flex items-center justify-center space-x-2 border border-white/10"
      >
        <span>⏩ Citation Suivante / Passer</span>
      </button>

      <button
        type="button"
        onClick={onResetGame}
        className="w-full sm:w-auto bg-red-950/40 hover:bg-red-900/60 text-red-300 font-semibold text-xs py-2.5 px-4 rounded-xl transition flex items-center justify-center space-x-1.5 border border-red-500/30"
      >
        <span>🔄 Réinitialiser la partie</span>
      </button>
    </div>
  );
};
export default GameControls;
