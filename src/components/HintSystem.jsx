import React from 'react';

export const HintSystem = ({ hints, revealedHints, onRevealHint }) => {
  if (!hints) return null;

  const hintTypes = [
    { type: 'year', label: 'Année', icon: '📅' },
    { type: 'genre', label: 'Genre', icon: '🎵' },
    { type: 'album', label: 'Album', icon: '💿' },
    { type: 'initials', label: 'Initiales', icon: '🔤' }
  ];

  return (
    <div className="space-y-3 my-4">
      <div className="flex items-center justify-between">
        <p className="text-xs uppercase font-semibold text-slate-400">Indices disponibles :</p>
        <span className="text-xs text-yellow-400 font-medium">(-20 pts par indice)</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {hintTypes.map(({ type, label, icon }) => (
          <button
            key={type}
            onClick={() => onRevealHint(type)}
            disabled={revealedHints.has(type)}
            className={`text-xs font-semibold py-2.5 px-3 rounded-xl transition flex items-center justify-center space-x-1.5 border ${
              revealedHints.has(type)
                ? 'bg-purple-950/80 border-purple-500 text-purple-300 opacity-80 cursor-default'
                : 'bg-white/5 hover:bg-purple-900/40 border-white/10 hover:border-purple-500 text-white'
            }`}
          >
            <span>{icon}</span> <span>{label}</span>
          </button>
        ))}
      </div>

      <div className="space-y-2 pt-1">
        {Array.from(revealedHints).map((type) => (
          <div key={type} className="bg-purple-950/70 border border-purple-500/40 text-purple-200 text-xs p-2.5 rounded-lg flex items-center">
            <span className="font-bold mr-2 uppercase">{type} :</span> <span>{hints[type]}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
export default HintSystem;
