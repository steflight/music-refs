import React from 'react';

export const ScoreBoard = ({ score, streak, highScore }) => {
  return (
    <header className="max-w-4xl mx-auto w-full mb-6">
      <div className="bg-slate-900/80 backdrop-blur-md rounded-2xl p-4 md:p-6 shadow-2xl flex flex-col md:flex-row justify-between items-center gap-4 border border-purple-500/30">
        
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-pink-500 to-cyan-400 animate-spin flex items-center justify-center p-0.5">
            <div className="w-full h-full bg-slate-950 rounded-full flex items-center justify-center">
              <span className="text-xs">🎵</span>
            </div>
          </div>
          <div>
            <h1 className="font-bold text-2xl tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-pink-500 via-purple-400 to-cyan-400">
              MUSIC REFS
            </h1>
            <p className="text-xs text-slate-400">Devinez l'artiste & la chanson</p>
          </div>
        </div>

        <div className="flex items-center space-x-6 bg-slate-950/60 px-5 py-2.5 rounded-xl border border-white/5">
          <div className="text-center">
            <p className="text-xs uppercase text-slate-400 font-semibold tracking-wider">Score</p>
            <p className="font-bold text-2xl text-cyan-400">{score}</p>
          </div>
          <div className="h-8 w-px bg-white/10"></div>
          <div className="text-center">
            <p className="text-xs uppercase text-slate-400 font-semibold tracking-wider">Série</p>
            <div className="flex items-center justify-center space-x-1">
              <span className="text-pink-500 text-sm">🔥</span>
              <span className="font-bold text-xl text-pink-500">{streak}</span>
            </div>
          </div>
          <div className="h-8 w-px bg-white/10"></div>
          <div className="text-center">
            <p className="text-xs uppercase text-slate-400 font-semibold tracking-wider">Record</p>
            <p className="font-bold text-xl text-yellow-400">{highScore}</p>
          </div>
        </div>
      </div>
    </header>
  );
};
export default ScoreBoard;
