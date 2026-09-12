# Music Refs — Backlog « Traction & Rétention »

Version 1.0 — 9 septembre 2026
Produit : music-refs-dev.kladriva.ca
Objectif du lot : transformer Music Refs d'un catalogue infini de citations en un rituel quotidien partageable (boucle Wordle + série Duolingo + récompense variable TikTok).

> Document de référence produit, archivé tel quel. Le suivi d'avancement et les écarts constatés sont dans [`../BACKLOG.md`](../BACKLOG.md).

Convention : chaque story a un ID (MR-xx), une priorité (P0 = bloque le lancement de la boucle, P1 = renforce la rétention, P2 = investissement long terme), des critères d'acceptation en Given/When/Then, et des notes techniques. L'ordre des épics est l'ordre de livraison recommandé.

---

## Épic 1 — Refs du jour (rendez-vous quotidien)

### MR-01 · Sélection déterministe des 5 refs du jour — P0

**En tant que** joueur, **je veux** que tout le monde reçoive les 5 mêmes citations chaque jour, **afin de** pouvoir comparer mon score avec mes amis.

Critères d'acceptation

- Given la date du jour (fuseau America/Toronto) et une catégorie, When le joueur ouvre le mode « Refs du jour », Then il reçoit exactement 5 citations, identiques pour tous les joueurs de cette catégorie ce jour-là.
- Given le jour change à 00:00 heure locale, When un joueur recharge la page, Then un nouveau set apparaît et l'ancien n'est plus jouable (sauf archive, voir MR-05).
- Given une citation a été « ref du jour » dans les 90 derniers jours, Then elle n'est pas resélectionnée.
- Given la catégorie « Toutes », Then le set contient au moins 3 catégories différentes.
- Then le numéro d'édition est affiché (« Refs du jour #1 » incrémenté quotidiennement à partir de la date de lancement).

Notes techniques

- Seed = hash(date ISO + catégorie) → générateur pseudo-aléatoire (ex. mulberry32) sur la liste triée par ID ; le calcul doit être reproductible côté serveur ET côté client.
- Prévoir une table `daily_sets(date, category, quote_ids[], edition)` matérialisée par un cron 00:00 pour figer le set (évite qu'un ajout de citation en journée change le set).
- Exposer `GET /api/daily?category=` retournant `{edition, date, quotes:[…sans réponse…]}` ; les réponses sont vérifiées côté serveur (`POST /api/daily/answer`) pour empêcher la triche via le DOM.

### MR-02 · Parcours de jeu du mode quotidien — P0

**En tant que** joueur, **je veux** jouer les 5 refs en moins de 2 minutes sans friction, **afin de** faire de ce jeu un réflexe quotidien.

Critères d'acceptation

- Given le joueur arrive sur la page d'accueil, Then le mode « Refs du jour » est le mode par défaut ; le mode infini existant devient « Continuer à jouer » accessible après le set du jour.
- Given une bonne réponse, When elle est validée, Then la citation suivante s'affiche automatiquement après 1,2 s max (animation de victoire incluse), sans clic « Suivant ».
- Given la touche Entrée dans le champ Titre, Then la réponse est validée (déjà le cas ? à vérifier).
- Given le joueur a répondu aux 5 citations (juste, faux ou passées), Then l'écran de fin (MR-03) s'affiche.
- Given le set du jour est déjà complété, When le joueur revient, Then il voit directement son écran de fin et un compte à rebours « Prochaines refs dans 06 h 12 ».
- Le bouton « Reset » n'apparaît pas dans le mode quotidien.

Notes techniques

- Persistance de l'état de la partie du jour en `localStorage` (clé `mr:daily:<date>:<category>`) puis en base si compte (MR-10).
- Prévoir un état par citation : `pending | correct | wrong | skipped | hintsUsed:n`.

### MR-03 · Écran de fin et bloc emoji partageable — P0

**En tant que** joueur, **je veux** un résumé visuel de ma partie copiable en un tap, **afin de** montrer mon score à mes amis sans dévoiler les réponses.

Critères d'acceptation

- Given la partie du jour terminée, Then l'écran de fin affiche : score du jour, nombre de bonnes réponses sur 5, indices utilisés, série en cours (MR-06), temps total.
- Then un bloc texte est généré au format exact :

  ```
  Music Refs #112 🎤 Rap FR
  🟩🟩🟨⬛🟩  4/5
  🔥 Série : 7 jours
  music-refs.kladriva.ca
  ```

  Légende : 🟩 trouvé sans indice, 🟨 trouvé avec indice(s), ⬛ raté/passé. Aucun nom d'artiste ni titre dans le bloc.
- Given le bouton « Partager », When il est cliqué sur mobile, Then la Web Share API est appelée avec le bloc ; en fallback (desktop / API absente) le bloc est copié dans le presse-papiers avec un toast « Copié ! ».
- Then un bouton secondaire « Envoyer sur WhatsApp » ouvre `https://wa.me/?text=<bloc encodé>`.
- Then le lien du bloc contient un paramètre `?ref=share` pour mesurer les arrivées via partage.

Notes techniques

- `navigator.share` détecté avec `navigator.canShare` ; conserver le texte tel quel (pas de HTML).
- Événement analytics `share_clicked {channel}` (voir MR-13).

### MR-04 · Révélation des réponses après la partie — P1

**En tant que** joueur, **je veux** voir les réponses et écouter un extrait après la partie, **afin de** apprendre ce que j'ai raté et ressentir une récompense.

Critères d'acceptation

- Given l'écran de fin, Then chaque citation ratée affiche artiste + titre et, si disponible, un lien d'écoute (Spotify/YouTube/Deezer) ouvert dans un nouvel onglet.
- Then les réponses ne sont accessibles qu'après la 5e citation (pas de spoiler en cours de partie).

Notes techniques

- Ajouter un champ optionnel `listen_url` dans le modèle citation ; remplissage manuel ou via recherche Spotify API dans l'admin.

### MR-05 · Archive des éditions précédentes — P2

**En tant que** nouveau joueur, **je veux** rejouer les éditions passées, **afin de** m'entraîner sans attendre demain.

Critères d'acceptation

- Given la liste des éditions passées, When j'en choisis une, Then je la joue avec le même parcours, mais le score ne compte ni pour la série ni pour le classement, et le bloc de partage est marqué « (archive) ».

---

## Épic 2 — Série quotidienne (loss aversion)

### MR-06 · Compteur de jours consécutifs — P0

**En tant que** joueur, **je veux** voir combien de jours d'affilée j'ai joué, **afin de** avoir une raison de revenir demain.

Critères d'acceptation

- Given le joueur termine le set du jour (au moins 1 citation répondue), Then sa série passe à N+1 si le set de la veille a été terminé, sinon repart à 1.
- Then la série s'affiche dans l'en-tête avec 🔥 et remplace l'actuel « Série » (qui compte les bonnes réponses d'affilée en partie : renommer celui-ci « Combo » pour éviter la confusion).
- Given un jalon atteint (3, 7, 14, 30, 100 jours), Then un écran de célébration plein écran apparaît une seule fois, avec le bloc partageable « 🔥 30 jours de Music Refs ».
- Given la série est en danger (set du jour non commencé après 20 h locale), Then l'en-tête affiche une pastille « Série en danger ».

Notes techniques

- Stockage : `{currentStreak, longestStreak, lastCompletedDate}` en localStorage, synchronisé avec le compte si connecté.
- Le calcul se fait sur la date locale du navigateur, mais la validation serveur utilise `daily_sets.date` pour éviter les manipulations d'horloge.

### MR-07 · Gel de série — P1

**En tant que** joueur, **je veux** un joker qui protège ma série si je rate un jour, **afin de** ne pas abandonner après un oubli.

Critères d'acceptation

- Given un nouveau joueur, Then il dispose d'un gel gratuit ; un second gel se gagne tous les 7 jours de série (max 2 en stock).
- Given un jour manqué et un gel disponible, When le joueur revient, Then le gel est consommé automatiquement, la série est conservée et un message l'explique.
- Given aucun gel disponible, Then la série repart à 0 et le message propose « Rejoue aujourd'hui pour repartir ».

### MR-08 · Rappel quotidien — P1

**En tant que** joueur, **je veux** recevoir un rappel si je n'ai pas joué, **afin de** ne pas perdre ma série.

Critères d'acceptation

- Given le joueur accepte les notifications (demande affichée seulement après la 2e partie terminée, jamais à la première visite), Then une notification push est envoyée à 19 h locale si le set du jour n'est pas terminé, texte : « 🔥 Ta série de N jours expire dans 5 h. Les refs du jour t'attendent. »
- Then il peut désactiver le rappel dans les réglages.

Notes techniques

- PWA + Service Worker + Web Push (VAPID). Prévoir un manifest (installable sur l'écran d'accueil, icône, couleur de thème).
- Stocker le fuseau du joueur pour planifier l'envoi côté serveur.

---

## Épic 3 — Récompense variable et feedback (effet TikTok)

### MR-09 · Rareté des citations — P1

**En tant que** joueur, **je veux** que certaines citations soient « rares » ou « légendaires », **afin de** ressentir une surprise à chaque nouvelle carte.

Critères d'acceptation

- Given le modèle citation, Then il possède un champ `rarity ∈ {commune, rare, légendaire}` (défaut : commune), éditable dans l'admin.
- Then les points sont multipliés : commune ×1, rare ×2, légendaire ×3 ; les indices coûtent proportionnellement.
- Given une citation rare ou légendaire s'affiche, Then la carte a une bordure et un fond distincts (rare : cyan animé ; légendaire : dégradé doré) et un badge visible avant de répondre.
- Given le set du jour, Then il contient au maximum 1 légendaire et au moins 1 commune.
- Then le bloc emoji (MR-03) utilise 🟪 pour une légendaire trouvée.

### MR-10 · Micro-feedback de victoire et d'échec — P1

**En tant que** joueur, **je veux** que chaque bonne réponse soit physiquement satisfaisante, **afin de** vouloir enchaîner.

Critères d'acceptation

- Given une bonne réponse, Then : animation de confettis courte (≤ 800 ms), compteur de score qui « roule » jusqu'à la nouvelle valeur, vibration haptique 30 ms sur mobile (`navigator.vibrate`), son court optionnel (coupé par défaut, mémorisé).
- Given une mauvaise réponse, Then : secousse horizontale du champ (≤ 300 ms), message court et bienveillant (« Presque ! ») — jamais de rouge plein écran.
- Given le joueur a activé « Réduire les animations » dans son OS (`prefers-reduced-motion`), Then les animations sont remplacées par un simple changement de couleur.

### MR-11 · Tolérance de saisie — P1

**En tant que** joueur, **je veux** que « dadju », « Dadju » ou « DADJU » soient acceptés, **afin de** ne pas être puni pour une faute de frappe.

Critères d'acceptation

- Then la comparaison ignore casse, accents, ponctuation, articles initiaux (« le/la/les ») et espaces multiples.
- Then une distance de Levenshtein ≤ 2 (pour les mots de ≥ 6 lettres) est acceptée.
- Then les alias d'artiste sont gérés (`aliases[]` dans le modèle : ex. « PNL », « P.N.L », « Booba » / « B2O »).
- Given le titre seul est faux mais l'artiste juste, Then la moitié des points est attribuée et un message l'indique.

---

## Épic 4 — Identité et social

### MR-12 · Pseudo léger sans compte — P0

**En tant que** joueur, **je veux** choisir un pseudo sans créer de compte, **afin de** apparaître au classement sans friction.

Critères d'acceptation

- Given la première fin de partie, Then une invite propose un pseudo (3–16 caractères, unicité non requise, filtre de mots interdits) ; ignorable.
- Then le pseudo est stocké localement avec un identifiant anonyme (UUID) et envoyé avec chaque score.
- Given un compte créé plus tard (email magic link ou Google), Then l'historique local (série, scores, gels) est fusionné dans le compte.

### MR-13 · Classement du jour — P1

**En tant que** joueur, **je veux** voir mon rang du jour, **afin de** prouver ma culture musicale.

Critères d'acceptation

- Given l'écran de fin, Then j'y vois « Tu es 37e sur 412 aujourd'hui (Rap FR) » et le Top 10 (pseudo, score, temps, indices).
- Then le classement est par édition et par catégorie ; réinitialisé chaque jour ; départage : score, puis nombre d'indices, puis temps.
- Then un onglet « Amis » filtre le classement sur les joueurs ayant joué au moins une Partie amis avec moi.

Notes techniques

- `POST /api/daily/result {edition, category, playerId, score, hints, timeMs, grid}` ; anti-triche minimale : refuser un temps < 3 s par citation et vérifier les réponses côté serveur (MR-01).

### MR-14 · Défi asynchrone entre amis — P1

**En tant que** joueur, **je veux** défier un ami sur mon set du jour et voir son résultat quand il a joué, **afin de** créer une rivalité sans devoir être connectés en même temps.

Critères d'acceptation

- Given l'écran de fin, When je clique « Défier un ami », Then un lien `/d/<code>` est généré et partagé (Web Share / WhatsApp).
- Given l'ami ouvre le lien, Then il joue le même set (même édition/catégorie) puis voit la comparaison face à face (score, grille emoji, temps).
- Given l'ami a terminé, Then je reçois une notification (si activée) « Karim a fait 5/5 sur ton défi 😱 ».
- Then la « Partie amis » synchrone existante reste disponible, sous le nom « Salon en direct ».

### MR-15 · Profil de culture musicale — P2

**En tant que** joueur, **je veux** une carte de profil qui résume mes forces par catégorie, **afin de** la partager en screenshot.

Critères d'acceptation

- Given au moins 20 citations répondues, Then une page `/profil` affiche un radar ou des barres par catégorie (% de réussite), le titre de « grade » (ex. « Encyclopédie du Rap FR »), la meilleure série et le nombre de légendaires trouvées.
- Then un bouton « Télécharger l'image » génère un PNG 1080×1920 (format story) via canvas.

---

## Épic 5 — Contenu communautaire (investissement)

### MR-16 · Proposer une punchline — P2

**En tant que** joueur, **je veux** soumettre mes propres citations, **afin de** contribuer au jeu et voir ma ref jouée par les autres.

Critères d'acceptation

- Given le formulaire `/proposer`, Then il demande : citation, artiste, titre, catégorie, année (optionnel), lien d'écoute (optionnel).
- Then la soumission part en statut `pending` dans l'admin existant avec le pseudo du contributeur.
- Given la citation est approuvée, Then elle est jouable et affiche « Proposée par <pseudo> » sur l'écran de révélation ; le contributeur reçoit +50 points et un badge « Contributeur ».
- Then un doublon évident (même artiste + même texte normalisé) est refusé à la soumission.

### MR-17 · Vote sur les citations — P2

**En tant que** joueur, **je veux** noter une citation après y avoir répondu, **afin de** que les meilleures remontent.

Critères d'acceptation

- Given l'écran de révélation, Then deux boutons 🔥 / 👎 sont disponibles (un seul vote par joueur par citation).
- Then les citations avec un ratio 👎 > 40 % sur ≥ 30 votes sont signalées dans l'admin.

---

## Épic 6 — Interface et mesure

### MR-18 · Retouches de l'en-tête et du Reset — P0

**En tant que** joueur, **je veux** que mes stats soient au centre et ne jamais tout perdre par erreur, **afin de** me sentir en confiance.

Critères d'acceptation

- Then le cartouche Score / Série / Record est déplacé sous le logo, pleine largeur sur mobile, chiffres ≥ 28 px.
- Then le bouton « Reset » est retiré de la zone de jeu et déplacé dans un menu « ⋯ » avec confirmation (« Effacer ma progression ? »).
- Then la page respecte un viewport mobile 360 px sans défilement horizontal, cible tactile ≥ 44 px.

### MR-19 · Événements analytics — P0

**En tant que** fondateur, **je veux** mesurer la boucle, **afin de** savoir si la traction est réelle.

Critères d'acceptation

- Then les événements suivants sont envoyés (outil : Plausible/Umami/PostHog au choix, sans cookie tiers) : `daily_started`, `daily_completed {score, hints, timeMs}`, `share_clicked {channel}`, `share_landed {ref}`, `streak_milestone {days}`, `challenge_created`, `challenge_accepted`, `notif_optin`, `quote_submitted`.
- Then un tableau de bord affiche : DAU, rétention J1/J7/J30, % de parties partagées, k-factor approximatif (arrivées `?ref=share` / parties terminées).

---

## Hors code — expérience « qui ne scale pas » (à faire en parallèle, par Stéphane)

Pendant 14 jours, avant ou pendant le développement de l'Épic 1 : poster manuellement chaque matin les 5 refs du jour (texte brut + lien) dans 3 groupes WhatsApp cibles ; noter chaque jour le nombre de réponses, de personnes qui renvoient leur score, et de demandes de « la suite ». Critère de validation : au moins 5 personnes qui répondent spontanément 5 jours de suite. Si le critère n'est pas atteint, revoir la proposition de valeur avant d'ouvrir les Épics 2 à 5.

## Ordre de livraison proposé

Sprint 1 (P0) : MR-18, MR-19, MR-01, MR-02, MR-03, MR-06, MR-12.
Sprint 2 (P1) : MR-11, MR-10, MR-09, MR-13, MR-07, MR-04.
Sprint 3 (P1/P2) : MR-08, MR-14, MR-15.
Sprint 4 (P2) : MR-16, MR-17, MR-05.

## Définition of Done commune

Testé sur mobile (Android Chrome + iOS Safari) et desktop ; aucune régression sur le mode infini et la Partie amis ; textes en français sans anglicisme inutile ; événements analytics vérifiés ; démo validée par Stéphane.
