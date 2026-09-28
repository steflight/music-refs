# Cahier des charges — App mobile Music Refs

Sep 27, 2026 · @stephane

Révision du Sep 27, 2026 : développement en natif (Swift / SwiftUI pour iOS, Kotlin / Jetpack Compose pour Android) au lieu d'une base de code multiplateforme ; planning et risques mis à jour.

Révision du Sep 28, 2026 : validation différée des réponses hors ligne, iOS 17 minimum, jeton anonyme pour les joueurs sans compte, notifications envoyées par le serveur pour les parties amis.

## Contexte et objectifs

L'app mobile porte Music Refs sur iOS et Android pour bâtir une audience fidèle, en restant non commercial jusqu'à la signature de licences.

Music Refs est aujourd'hui un jeu web ([music-refs-dev.kladriva.ca](https://music-refs-dev.kladriva.ca/)) : le joueur lit une punchline ou une citation musicale et devine l'artiste et le titre. La base compte environ 2 274 citations. Le site propose déjà un mode infini, un rituel quotidien « Refs du jour », des indices payants en points, des combos, des séries avec « gel » et un mode « Partie amis ».

Objectifs de l'app :

- Faire du rituel quotidien une habitude, grâce aux notifications et au partage des résultats.
- Rendre la révélation plus forte, avec la pochette, l'extrait audio et un lien d'écoute vers l'artiste.
- Mesurer l'audience et les écoutes générées, pour négocier ensuite des licences avec des chiffres.
- Respecter strictement le cadre non commercial et les droits des artistes pendant la phase 1.

## Périmètre et phasage

Ce cahier des charges couvre en détail la phase 1 ; les phases 2 et 3 sont cadrées pour que l'architecture les anticipe.

&#91;embedded content: feuille de route · 3 phases, 1 porte\]

La phase 3 ne démarre qu'une fois les licences obtenues et le montage validé par un juriste. Aucune fonction payante n'est développée avant, mais le code prévoit l'emplacement du premium (drapeaux de fonctionnalités).

Hors périmètre phase 1 : publicité, achats intégrés, dons, vente de données, hébergement de fichiers audio, affichage de paroles complètes.

## Utilisateurs cibles et parcours

La cible principale est le fan de rap et de musiques urbaines francophones qui joue quelques minutes par jour et partage ses scores.

| Profil | Attente principale | Usage type |
| --- | --- | --- |
| Fan quotidien | Rituel court, série à protéger | 1 partie Refs du jour par jour, 2 à 3 min |
| Joueur compétitif | Score, classements, combos | Sessions en mode infini, 10 à 20 min |
| Groupe d'amis | Défier ses proches | Parties amis, partage de résultats |
| Curieux musical | Découvrir des morceaux | Écoute des extraits, clic vers Deezer ou Spotify |

Parcours principaux :

1. **Première ouverture** : écran de règles en 3 cartes, partie d'essai guidée, puis création facultative d'un pseudo.
2. **Rituel quotidien** : notification → Refs du jour (5 citations) → révélation après chaque réponse → carte de résultat à partager. Hors ligne : réponses enregistrées sans verdict, révélations et carte de résultat à la synchronisation.
3. **Mode infini** : choix de catégorie et de difficulté → enchaînement des citations → record personnel.
4. **Partie amis** : création d'un défi → lien d'invitation → mêmes citations pour tous → classement du défi.
5. **Découverte** : révélation → extrait audio → « Écouter le morceau » sur la plateforme de l'utilisateur.

## Fonctionnalités

Le MVP reprend le jeu web et ajoute ce que le mobile fait mieux : notifications, partage natif, audio et révélation soignée.

| Fonctionnalité | Description | Priorité | Phase |
| --- | --- | --- | --- |
| Refs du jour | 5 citations identiques pour tous, une fois par jour, numérotées (#18, #19…) | Indispensable | 1 |
| Mode infini | Enchaînement aléatoire, filtre par catégorie et difficulté | Indispensable | 1 |
| Saisie de réponse | Autocomplétion artistes et titres, tolérance aux fautes et aux accents | Indispensable | 1 |
| Indices | Année, genre, album, initiales, -20 pts chacun | Indispensable | 1 |
| Score et progression | Score, combo, record, série quotidienne, « gel » de série | Indispensable | 1 |
| Écran de révélation | Pochette, artiste, titre, album, extrait 30 s Deezer, boutons d'écoute | Indispensable | 1 |
| Carte de résultat | Grille d'emojis + score, partage natif (WhatsApp, Instagram, X, TikTok) | Indispensable | 1 |
| Notifications | Rappel quotidien à l'heure choisie, alerte de série en danger, résultat prêt après une partie hors ligne, activité des parties amis | Indispensable | 1 |
| Accueil et règles | 3 cartes d'explication + partie d'essai | Indispensable | 1 |
| Profil léger | Pseudo, avatar généré, statistiques ; compte facultatif | Important | 1 |
| Partie amis | Défi par lien, mêmes citations, classement du défi | Important | 1 |
| Signaler une citation | Erreur de réponse ou demande de retrait, depuis la révélation | Indispensable | 1 |
| Mode blind test audio | Deviner à partir de l'extrait Deezer, sans texte | Important | 2 |
| Classements | Hebdomadaire, par pays, entre amis | Important | 2 |
| Packs thématiques | Rap FR, Afro / Bénin, Québec, Gospel, Années 2000 | Important | 2 |
| Badges | Objectifs de série, de genre, de découverte | Souhaitable | 2 |
| Artiste du mois | Sélection mise en avant avec l'accord de l'artiste | Souhaitable | 2 |
| Premium | Statistiques avancées, parties privées, packs exclusifs, sans aucune pub | Bloqué par la porte | 3 |

Règles de jeu à conserver : validation si l'artiste **ou** le titre est trouvé (points partiels), bonus si les deux, combo remis à zéro en cas d'échec ou de passage.

## Contenu, droits d'auteur et conformité

En phase 1, l'app ne génère aucun revenu direct ou indirect et n'utilise que des extraits courts, crédités et retirables sur demande.

**Citations (texte)**

- Une seule ligne par citation, jamais un couplet ni un refrain entier.
- Pas plusieurs citations d'un même titre qui reconstitueraient le texte ; plafond paramétrable côté back-office.
- Aucun écran pour parcourir ou rechercher toute la base de citations.
- Artiste, titre et album crédités à chaque révélation, avec lien vers l'écoute officielle.

**Audio et visuels**

- Extraits de 30 s via l'API publique Deezer, avec la mention « Audio fourni par Deezer » et le lien vers le titre ([conditions Deezer](https://developers.deezer.com/termsofuse)).
- Lien d'extrait demandé au moment de jouer : jamais stocké, jamais téléchargé, jamais mis en cache sur l'appareil.
- Seul l'identifiant Deezer du titre est enregistré en base.
- Pochettes affichées depuis l'URL Deezer, non hébergées.

**Retraits et ayants droit**

- Page « Artistes et ayants droit » dans l'app et sur le web, avec formulaire de retrait.
- Retrait d'une citation désactivable en un clic depuis le back-office, effectif sous 48 h maximum.
- Journal des demandes et des retraits conservé.

**Vie privée et stores**

- Compte facultatif ; données minimales (pseudo, scores, préférences de notification). Sans compte, le joueur est identifié par un jeton anonyme, sans lien avec son identité ni avec un identifiant publicitaire.
- Mesure d'audience sans cookies publicitaires ni revente de données ; politique de confidentialité conforme à la Loi 25 (Québec) et au RGPD pour les joueurs européens.
- Fiches App Store et Google Play : app gratuite, sans achats intégrés ni publicité, classification d'âge adaptée aux paroles citées.
- Pas de logos d'artistes ni de marques dans les visuels de l'app ou des fiches stores.

Validation juridique : relecture de ce cadre par un juriste en propriété intellectuelle avant la publication sur les stores.

## Exigences techniques et architecture

L'app réutilise le back-end du site web, étendu en API ; elle appelle Deezer directement depuis l'appareil pour que chaque joueur ait son propre quota.

&#91;embedded content: architecture cible · 6 composants\]

Le serveur n'enregistre que l'identifiant Deezer de chaque titre ; l'app demande le lien d'extrait au moment de la révélation.

| Sujet | Exigence |
| --- | --- |
| Technologie | Natif sur chaque plateforme : Swift / SwiftUI pour iOS, Kotlin / Jetpack Compose pour Android. Choix motivé par la fluidité, l'audio, l'haptique, les notifications et le partage natifs |
| Cohérence iOS / Android | Contrat d'API commun (OpenAPI) dont sont générés les clients des deux apps ; règles de jeu, validation des réponses et calcul du score côté serveur, jamais recodés dans chaque app ; textes externalisés partagés |
| Plateformes | iOS 17+ et Android 8+ (API 26), téléphones d'abord, tablettes compatibles. iOS 17 permet d'utiliser SwiftUI moderne (navigation, suivi d'état) sans solutions de contournement |
| API | REST ou GraphQL versionnée, authentification par jeton, limitation de débit côté serveur |
| Identité | Jeton anonyme créé par le serveur à la première ouverture, stocké de façon sécurisée (Keychain iOS, Keystore Android) ; séries, scores et parties amis rattachés à ce jeton ; rattachement au compte si le joueur en crée un, sans perte de progression |
| Deezer | Appels côté appareil, gestion des erreurs de quota avec nouvel essai différé et repli sans audio |
| Refs du jour | Tirage côté serveur, identique pour tous, bascule à minuit heure de Montréal (fuseau à confirmer) |
| Hors ligne | Validation différée. Refs du jour préchargé : texte des 5 citations seulement, sans réponses ni indices. Hors ligne, chaque réponse est enregistrée avec son heure de saisie, sans verdict, et ne peut plus être modifiée ; les indices sont indisponibles. Au retour du réseau, le serveur valide les réponses et calcule score et combos ; une notification locale annonce le résultat, puis le joueur voit les révélations complètes et la carte de résultat. La série est conservée si les réponses sont saisies avant la bascule du jour et reçues par le serveur dans les 48 h. Mode infini et parties amis nécessitent le réseau ; audio indisponible hors ligne |
| Notifications | Rappel quotidien, alerte de série et résultat prêt : notifications locales programmées sur l'appareil. Parties amis (ami qui relève le défi, classement final) : notifications envoyées par le serveur via APNs (iOS) et FCM (Android) |
| Performance | Ouverture à froid sous 2 s, citation suivante sous 300 ms, démarrage de l'extrait sous 1 s en 4G |
| Sécurité | Back-office hors de l'app et protégé, lien Admin retiré des écrans publics, réponses vérifiées côté serveur (pas de solution envoyée à l'app avant la réponse) |
| Premium futur | Drapeaux de fonctionnalités prêts, aucun module de paiement intégré en phase 1 |
| Langues | Français au lancement, anglais prévu (textes externalisés) |

## UX/UI et identité visuelle

L'app garde l'univers néon sombre du site et met l'accent sur un moment fort : la révélation.

- **Identité** : reprise du logo, des dégradés rose-violet et cyan et des typographies du site ; thème sombre par défaut, thème clair en option.
- **Écran de jeu** : la citation occupe le haut de l'écran, les champs de réponse restent visibles au-dessus du clavier, indices en une rangée de 4 boutons.
- **Révélation** : animation courte (moins de 1 s), pochette en grand, extrait lancé d'un geste, boutons « Écouter sur Deezer » et « Écouter sur Spotify », retour haptique sur bonne réponse.
- **Carte de résultat** : format carré et format story (9:16), générée sans reprendre le texte des citations, seulement le score et la grille.
- **Sons** : effets courts désactivables, jamais de musique non licenciée.
- **Accessibilité** : contrastes WCAG AA, tailles de texte dynamiques, lecteur d'écran sur tous les boutons, audio jamais indispensable pour jouer en mode texte.
- **Livrables design** : maquettes Figma des 12 écrans clés (accueil, règles, jeu, révélation, résultat, infini, amis, profil, statistiques, réglages, ayants droit, signalement) et prototype cliquable.

## Mesure d'audience et indicateurs

Les indicateurs servent deux buts : améliorer le jeu et prouver aux artistes et labels que l'app leur apporte des écoutes.

| Indicateur | Définition | Usage |
| --- | --- | --- |
| Joueurs actifs | Quotidiens, hebdomadaires, mensuels | Taille de l'audience |
| Rétention | Part des joueurs revenus à J1, J7, J30 | Qualité du rituel |
| Séries | Longueur moyenne et médiane des séries quotidiennes | Engagement |
| Parties jouées | Par mode (jour, infini, amis) | Priorités produit |
| Taux de réussite | Par citation et par catégorie | Réglage de la difficulté |
| Partages | Cartes de résultat partagées, installations issues d'un lien | Croissance |
| Écoutes d'extraits | Par artiste et par titre | Argument ayants droit |
| Clics vers les plateformes | « Écouter sur Deezer / Spotify », par artiste | Argument ayants droit |
| Demandes de retrait | Nombre et délai de traitement | Conformité |

Outil : analytique respectueuse de la vie privée, sans identifiant publicitaire (par exemple Aptabase ou PostHog auto-hébergé). Un tableau de bord mensuel par artiste est exporté pour les prises de contact de la phase 2.

## Planning, livrables et critères d'acceptation

La phase 1 est estimée à environ 14 semaines, en 5 lots successifs, avec un développeur iOS et un développeur Android en parallèle à partir du lot 3. Avec un seul développeur mobile, compter 16 à 18 semaines : les lots 3 et 4 coûtent 1,6 à 2 fois plus qu'avec une base de code unique. Ces durées sont indicatives et à confirmer avec l'équipe.

| Lot | Contenu | Livrables | Durée estimée |
| --- | --- | --- | --- |
| 1. Cadrage et design | Parcours, maquettes (conventions iOS et Android), validation juridique du cadre de contenu | Maquettes Figma, prototype, note juridique | 2 semaines |
| 2. API et back-office | Extension de l'API du site, contrat OpenAPI, jeton anonyme, Refs du jour côté serveur, validation des réponses (en ligne et différée), retraits, envoi des notifications APNs / FCM | API documentée, back-office à jour | 3 semaines |
| 3. App — cœur du jeu | Jeu, indices, scores, séries, révélation, audio Deezer, développés en parallèle sur iOS et Android | Build de test iOS et Android | 5 semaines |
| 4. Social et rétention | Partage, notifications, parties amis, profil, analytique, sur les deux plateformes | Build bêta iOS et Android | 3 semaines |
| 5. Bêta et publication | Bêta fermée (TestFlight, test interne Play), corrections, fiches stores | App publiée sur les deux stores | 1 semaine + délais de revue |

Critères d'acceptation de la phase 1 :

- [ ] Une partie Refs du jour complète se joue en moins de 3 minutes, sans bug bloquant.
- [ ] Les 5 citations du jour sont identiques pour tous les joueurs.
- [ ] Chaque révélation affiche le crédit complet, l'attribution Deezer et au moins un lien d'écoute.
- [ ] Aucun fichier audio ni lien d'extrait n'est stocké sur le serveur ou l'appareil.
- [ ] Une citation retirée dans le back-office disparaît de l'app sans nouvelle version.
- [ ] Aucune publicité, aucun achat intégré, aucun SDK publicitaire dans le build.
- [ ] Refs du jour déjà chargé se joue sans réseau ; score, révélations et série sont attribués à la synchronisation, sans perte de série.
- [ ] Aucune solution (artiste, titre, album, initiales) n'est présente sur l'appareil avant la réponse, en ligne comme hors ligne.
- [ ] Les objectifs de performance de la section technique sont atteints sur un Android d'entrée de gamme.
- [ ] Le cadre de contenu a été validé par un juriste avant la soumission aux stores.

## Risques et points ouverts

Le risque principal est juridique ; il est réduit par le cadre non commercial et un processus de retrait rapide, pas supprimé.

| Risque | Impact | Parade |
| --- | --- | --- |
| Demande de retrait d'un ayant droit | Citations ou artistes à retirer | Retrait en un clic, délai de 48 h, journal des demandes |
| Changement des conditions de l'API Deezer | Perte de l'audio | Mode texte autonome, repli vers les lecteurs intégrés officiels |
| Refus d'une fiche par Apple ou Google | Retard de publication | Fiches sans marques d'artistes, mention claire du cadre non commercial |
| Quota Deezer dépassé | Extraits indisponibles un instant | Appels depuis l'appareil, nouvel essai différé |
| Faible rétention | Audience trop petite pour négocier | Notifications, séries, partage, packs thématiques |
| Tentation de monétiser tôt | Exposition juridique plus forte | Porte explicite : licences signées + validation juridique |
| Écarts entre les apps iOS et Android | Règles ou affichages différents selon la plateforme | Contrat OpenAPI commun, logique de jeu côté serveur, recette croisée sur les deux plateformes |
| Triche sur une partie hors ligne | Séries ou scores gonflés | Réponses non modifiables, délai de synchronisation limité à 48 h, parties hors ligne exclues des classements en phase 2 |
| Coût de deux bases de code | Planning et maintenance plus lourds | Développement en parallèle, fonctionnalités livrées sur les deux plateformes dans le même lot |

Points ouverts :

- [ ] Stack actuelle du site (langage, base de données, hébergement) à confirmer pour définir l'extension de l'API.
- [ ] Fuseau de référence de Refs du jour : Montréal, Cotonou ou heure locale du joueur.
- [ ] Nom de l'app sur les stores et compte développeur (Kladriva ou entité dédiée).
- [ ] Choix de l'outil d'analytique.
- [ ] Liste des premiers artistes à contacter pour la phase 2.
- [ ] Juriste en propriété intellectuelle à identifier.
