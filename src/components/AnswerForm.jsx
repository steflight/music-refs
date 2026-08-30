import React, { useState } from 'react';

export const AnswerForm = ({ onSubmitAnswer, artistGuessed, titleGuessed, isFullyGuessed }) => {
  const [artistInput, setArtistInput] = useState('');
  const [titleInput, setTitleInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmitAnswer(artistInput, titleInput);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 pt-2">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">Nom de l'Artiste / Groupe</label>
          <input
            type="text"
            value={artistInput}
            onChange={(e) => setArtistInput(e.target.value)}
            disabled={artistGuessed || isFullyGuessed}
            placeholder="Ex: Ninho, PNL..."
            className="w-full bg-black/60 border border-white/15 focus:border-cyan-400 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 outline-none transition disabled:opacity-50"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">Titre de la Chanson</label>
          <input
            type="text"
            value={titleInput}
            onChange={(e) => setTitleInput(e.target.value)}
            disabled={titleGuessed || isFullyGuessed}
            placeholder="Ex: Jefe, A l'ammoniaque..."
            className="w-full bg-black/60 border border-white/15 focus:border-pink-500 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 outline-none transition disabled:opacity-50"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={isFullyGuessed}
        className="w-full bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 text-white font-bold py-3.5 px-6 rounded-xl shadow-lg transition transform active:scale-95 disabled:opacity-50"
      >
        🎯 Valider ma réponse
      </button>
    </form>
  );
};
export default AnswerForm;
