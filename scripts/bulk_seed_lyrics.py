#!/usr/bin/env python3
"""Bulk-import punchlines via Music Refs admin API + LRCLIB.

Usage:
  ADMIN_TOKEN=... python3 scripts/bulk_seed_lyrics.py [--target 1000] [--per-track 8]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict

import httpx

# artist, title, category_ids
# 1=rap-fr 2=slow 3=variété 4=international 5=anglais 7=mbole 9=gospel
CATALOG: list[tuple[str, str, list[int]]] = [
    # --- Dadju (slow / R&B) ---
    ("Dadju", "Jaloux", [2]),
    ("Dadju", "Reine", [2]),
    ("Dadju", "Compliqué", [2]),
    ("Dadju", "Bobo", [2]),
    ("Dadju", "Django", [2]),
    ("Dadju", "Lionel", [2]),
    ("Dadju", "Makila", [2]),
    ("Dadju", "Maamou", [2]),
    ("Dadju", "Perdu", [2]),
    ("Dadju", "Grand bain", [2]),
    ("Dadju", "Mon soleil", [2]),
    ("Dadju", "Tatami", [2]),
    ("Dadju", "Aloka", [2]),
    ("Dadju", "Mafuzzy Style", [2]),
    ("Dadju", "Dieu merci", [2]),
    ("Dadju", "Sans titre", [2]),
    ("Dadju", "I love you", [2]),
    ("Dadju", "Mwasi Ya Congo", [2]),
    ("Dadju", "Christina", [2]),
    ("Dadju", "Wouli Liya", [2]),
    ("Dadju", "Ma vie", [2]),
    ("Dadju", "Bad boy", [2]),
    ("Dadju", "Poison", [2]),
    ("Dadju", "Tout ou rien", [2]),
    ("Dadju", "Amour mon amour", [2]),
    ("Dadju", "Le droit à l'amour", [2]),
    ("Dadju", "Chérie Coco", [2]),
    ("Dadju", "Un jour peut-être", [2]),
    ("Dadju", "Vaillant", [2]),
    ("Dadju", "Robes", [2]),
    # --- Singuila ---
    ("Singuila", "C'est trop", [2]),
    ("Singuila", "Ma nature", [2]),
    ("Singuila", "Aïcha", [2]),
    ("Singuila", "J'oublie", [2]),
    ("Singuila", "Le misérable", [2]),
    ("Singuila", "Paramètre", [2]),
    ("Singuila", "Statut", [2]),
    ("Singuila", "Reviens-moi", [2]),
    ("Singuila", "Ma vie", [2]),
    ("Singuila", "J'aimerais", [2]),
    ("Singuila", "Le temps", [2]),
    ("Singuila", "Je t'aime", [2]),
    ("Singuila", "Fais-moi confiance", [2]),
    ("Singuila", "Ensemble", [2]),
    ("Singuila", "Je n'ai plus le cœur", [2]),
    ("Singuila", "La femme de quelqu'un", [2]),
    ("Singuila", "C'est ma go", [2]),
    ("Singuila", "Ne me dis pas", [2]),
    ("Singuila", "Pourquoi", [2]),
    ("Singuila", "On s'aimait", [2]),
    # --- M. Pokora / Matt Pokora ---
    ("M. Pokora", "Elle me contrôle", [3]),
    ("M. Pokora", "Juste une photo de toi", [3]),
    ("M. Pokora", "Catch me if you can", [3]),
    ("M. Pokora", "Cette année-là", [3]),
    ("M. Pokora", "Tombé", [3]),
    ("M. Pokora", "Si on disait", [3]),
    ("M. Pokora", "Belinda", [3]),
    ("M. Pokora", "De retour", [3]),
    ("M. Pokora", "Pas sans toi", [3]),
    ("M. Pokora", "Le monde", [3]),
    ("M. Pokora", "Qui on est", [3]),
    ("M. Pokora", "Comme d'habitude", [3]),
    ("M. Pokora", "On est là", [3]),
    ("M. Pokora", "Random", [3]),
    ("M. Pokora", "Wipa", [3]),
    ("Matt Pokora", "Parti trop tôt", [3]),
    ("Matt Pokora", "Showbiz", [3]),
    ("Matt Pokora", "La vie de star", [3]),
    ("Matt Pokora", "L'objet du désir", [3]),
    ("Matt Pokora", "Dangerous", [3]),
    ("Matt Pokora", "Mirage", [3]),
    ("Matt Pokora", "Wanna be startin' somethin", [3]),
    ("Matt Pokora", "Get up get down", [3]),
    ("Matt Pokora", "My Way", [3]),
    # --- Booba ---
    ("Booba", "DKR", [1]),
    ("Booba", "Validée", [1]),
    ("Booba", "Kalash", [1]),
    ("Booba", "Petite fille", [1]),
    ("Booba", "92i Veyron", [1]),
    ("Booba", "Caramel", [1]),
    ("Booba", "Avant de partir", [1]),
    ("Booba", "Jour de paye", [1]),
    ("Booba", "Madrina", [1]),
    ("Booba", "Friday", [1]),
    ("Booba", "Drapeau noir", [1]),
    ("Booba", "Ghetto Pharm", [1]),
    ("Booba", "Sagacité", [1]),
    ("Booba", "Garcimore", [1]),
    ("Booba", "Scarface", [1]),
    ("Booba", "Autobahn", [1]),
    ("Booba", "Salside", [1]),
    ("Booba", "Trône", [1]),
    ("Booba", "Safari", [1]),
    ("Booba", "Boy", [1]),
    ("Booba", "Sale époque", [1]),
    ("Booba", "Nero Nemesis", [1]),
    ("Booba", "Paname", [1]),
    ("Booba", "Tallac", [1]),
    ("Booba", "Le duc de Boulogne", [1]),
    ("Booba", "Médicament", [1]),
    ("Booba", "Ratpi World", [1]),
    ("Booba", "5G", [1]),
    ("Booba", "Élyséenne", [1]),
    ("Booba", "Joker", [1]),
    ("Booba", "King", [1]),
    ("Booba", "OKLM", [1]),
    ("Booba", "Billets verts", [1]),
    ("Booba", "Mové Lang", [1]),
    ("Booba", "Pitbull", [1]),
    ("Booba", "Zero", [1]),
    ("Booba", "Dolce Vita", [1]),
    ("Booba", "Lunatic", [1]),
    ("Booba", "Temps mort", [1]),
    ("Booba", "Garde la pêche", [1]),
    # --- Orelsan ---
    ("Orelsan", "Basique", [1]),
    ("Orelsan", "La quête", [1]),
    ("Orelsan", "Jour meilleur", [1]),
    ("Orelsan", "La pluie", [1]),
    ("Orelsan", "San", [1]),
    ("Orelsan", "Ils sont cools", [1]),
    ("Orelsan", "Notes pour trop tard", [1]),
    ("Orelsan", "Défaite de famille", [1]),
    ("Orelsan", "Rêves bizarres", [1]),
    ("Orelsan", "Tout va bien", [1]),
    ("Orelsan", "Civilisation", [1]),
    ("Orelsan", "L'odeur de l'essence", [1]),
    ("Orelsan", "Shonen", [1]),
    ("Orelsan", "Ensemble", [1]),
    ("Orelsan", "La lettre", [1]),
    ("Orelsan", "Jimmy Punchline", [1]),
    ("Orelsan", "La terre est ronde", [1]),
    ("Orelsan", "Plus rien ne m'étonne", [1]),
    ("Orelsan", "Changement", [1]),
    ("Orelsan", "Suicide social", [1]),
    ("Orelsan", "Pour le Pire", [1]),
    ("Orelsan", "Le chant des sirènes", [1]),
    ("Orelsan", "La fête est finie", [1]),
    ("Orelsan", "Paradis blanc", [1]),
    ("Orelsan", "Discipline", [1]),
    ("Orelsan", "Christophe", [1]),
    ("Orelsan", "La peur", [1]),
    ("Orelsan", "Rappeur de paname", [1]),
    ("Orelsan", "No life", [1]),
    ("Orelsan", "Quand est-ce que ça s'arrête", [1]),
    ("Orelsan", "Manifeste", [1]),
    ("Orelsan", "Dans ma ville on traine", [1]),
    ("Orelsan", "Baise le monde", [1]),
    ("Orelsan", "Toujours en retard", [1]),
    ("Orelsan", "Histoire secrète", [1]),
    # --- MHD ---
    ("MHD", "Afro Trap Part. 1", [1]),
    ("MHD", "Afro Trap Part. 2", [1]),
    ("MHD", "Afro Trap Part. 3", [1]),
    ("MHD", "Afro Trap Part. 4", [1]),
    ("MHD", "Afro Trap Part. 5", [1]),
    ("MHD", "Afro Trap Part. 6", [1]),
    ("MHD", "Afro Trap Part. 7", [1]),
    ("MHD", "Afro Trap Part. 8", [1]),
    ("MHD", "Afro Trap Part. 9", [1]),
    ("MHD", "Afro Trap Part. 10", [1]),
    ("MHD", "Afro Trap Part. 11", [1]),
    ("MHD", "Bébé", [1]),
    ("MHD", "La puissance", [1]),
    ("MHD", "Roger Milla", [1]),
    ("MHD", "A Kasa", [1]),
    ("MHD", "Bodyguard", [1]),
    ("MHD", "Ma vie", [1]),
    ("MHD", "Champions League", [1]),
    ("MHD", "Ngatie Abedi", [1]),
    ("MHD", "Molo Molo", [1]),
    ("MHD", "Mama", [1]),
    ("MHD", "Problèmes", [1]),
    ("MHD", "Interlude", [1]),
    ("MHD", "Tout seul", [1]),
    ("MHD", "Fais le mouv", [1]),
    ("MHD", "Bravo", [1]),
    ("MHD", "Mafuzzy Style", [1]),
    ("MHD", "Hé oh", [1]),
    ("MHD", "K.I.R.A.", [1]),
    ("MHD", "Afro Gucci Gang", [1]),
    # --- densification rap FR pour viser 1000+ ---
    ("Ninho", "Jefe", [1]),
    ("Ninho", "Méchant", [1]),
    ("Ninho", "Lettre à une femme", [1]),
    ("Ninho", "Goutte d'eau", [1]),
    ("Ninho", "Vrac", [1]),
    ("Ninho", "Fendi", [1]),
    ("Ninho", "Riquet", [1]),
    ("Ninho", "Boîte auto", [1]),
    ("Ninho", "Aïcha", [1]),
    ("Ninho", "Play", [1]),
    ("Ninho", "Maman ne le sait pas", [1]),
    ("Ninho", "La vie qu'on mène", [1]),
    ("Ninho", "Zipette", [1]),
    ("Ninho", "Coco", [1]),
    ("Ninho", "Yaya", [1]),
    ("Niska", "Réseaux", [1]),
    ("Niska", "Salé", [1]),
    ("Niska", "Médicament", [1]),
    ("Niska", "Bénéfice", [1]),
    ("Niska", "Du lundi au lundi", [1]),
    ("Niska", "W.L", [1]),
    ("Niska", "De l'ombre à la lumière", [1]),
    ("Niska", "Boomerang", [1]),
    ("Niska", "Carbo", [1]),
    ("Niska", "Valise", [1]),
    ("Damso", "Macarena", [1]),
    ("Damso", "Θ. Ipséité", [1]),
    ("Damso", "Nwaar Is The New Black", [1]),
    ("Damso", "Feu de bois", [1]),
    ("Damso", "J'ai trop fumé", [1]),
    ("Damso", "Paris c'est loin", [1]),
    ("Damso", "Graine de sablier", [1]),
    ("Damso", "Smog", [1]),
    ("Damso", "Amnésie", [1]),
    ("Damso", "Nardey", [1]),
    ("Damso", "Autotune", [1]),
    ("Damso", "Même problème", [1]),
    ("SCH", "Mannschaft", [1]),
    ("SCH", "Anarchie", [1]),
    ("SCH", "Fusil", [1]),
    ("SCH", "6.45i", [1]),
    ("SCH", "Otto", [1]),
    ("SCH", "Rêves de gosse", [1]),
    ("SCH", "Marché noir", [1]),
    ("SCH", "A7", [1]),
    ("SCH", "Gomorra", [1]),
    ("SCH", "Loup noir", [1]),
    ("Jul", "Toto et Ninetta", [1]),
    ("Jul", "Alors alors", [1]),
    ("Jul", "Je tourne en rond", [1]),
    ("Jul", "Wesh alors", [1]),
    ("Jul", "On m'appelle l'ovni", [1]),
    ("Jul", "Dans ma paranoïa", [1]),
    ("Jul", "Ça sent bon", [1]),
    ("Jul", "J'oublie tout", [1]),
    ("Jul", "Loin", [1]),
    ("Jul", "Tu la love", [1]),
    ("Gims", "Bella", [1, 2]),
    ("Gims", "Est-ce que tu m'aimes", [2]),
    ("Gims", "Sapés comme jamais", [1]),
    ("Gims", "J'me tire", [1]),
    ("Gims", "Zombie", [1]),
    ("Gims", "La même", [2]),
    ("Gims", "Hola Señorita", [2]),
    ("Gims", "Reste", [2]),
    ("Gims", "Malavita", [1]),
    ("Gims", "Le Pire", [1]),
    ("Stromae", "Papaoutai", [3]),
    ("Stromae", "Alors on danse", [3]),
    ("Stromae", "Formidable", [3]),
    ("Stromae", "Tous les mêmes", [3]),
    ("Stromae", "Santé", [3]),
    ("Stromae", "L'enfer", [3]),
    ("Stromae", "Fils de joie", [3]),
    ("Stromae", "Carmen", [3]),
    ("Stromae", "Ta fête", [3]),
    ("Stromae", "Ave Cesaria", [3]),
    ("Aya Nakamura", "Djadja", [2]),
    ("Aya Nakamura", "Pookie", [2]),
    ("Aya Nakamura", "Copines", [2]),
    ("Aya Nakamura", "Jolie nana", [2]),
    ("Aya Nakamura", "Soldat", [2]),
    ("Aya Nakamura", "Comportement", [2]),
    ("Aya Nakamura", "VIP", [2]),
    ("Aya Nakamura", "Dégaine", [2]),
    ("Aya Nakamura", "SMS", [2]),
    ("Aya Nakamura", "La dot", [2]),
    ("Nekfeu", "Égérie", [1]),
    ("Nekfeu", "On verra", [1]),
    ("Nekfeu", "Tempête", [1]),
    ("Nekfeu", "Humanoïde", [1]),
    ("Nekfeu", "Squa", [1]),
    ("Nekfeu", "Cybernétique", [1]),
    ("Nekfeu", "Mauvaise graine", [1]),
    ("Nekfeu", "Nekfeu", [1]),
    ("Nekfeu", "Risibles amours", [1]),
    ("Nekfeu", "Avant tu riais", [1]),
    ("PNL", "Le monde ou rien", [1]),
    ("PNL", "DA", [1]),
    ("PNL", "J'vendrai mon âme", [1]),
    ("PNL", "A l'ammoniaque", [1]),
    ("PNL", "Deux frères", [1]),
    ("PNL", "Au DD", [1]),
    ("PNL", "Bené", [1]),
    ("PNL", "Naha", [1]),
    ("PNL", "Onizuka", [1]),
    ("PNL", "Tant que Dieu me donne", [1]),
    ("Lomepal", "Trop beau", [1]),
    ("Lomepal", "Lucy", [1]),
    ("Lomepal", "Becte", [1]),
    ("Lomepal", "Palpal", [1]),
    ("Lomepal", "Mauvais ordre", [1]),
    ("Lomepal", "1000°C", [1]),
    ("Lomepal", "Summer Days", [1]),
    ("Lomepal", "Yeux disent", [1]),
    ("Lomepal", "Flash", [1]),
    ("Lomepal", "Soleil", [1]),
    ("Vald", "Eurotrap", [1]),
    ("Vald", "Réflexions narcissiques", [1]),
    ("Vald", "Bonjour", [1]),
    ("Vald", "Désaccordé", [1]),
    ("Vald", "Journal Perso II", [1]),
    ("Vald", "Selfie", [1]),
    ("Vald", "Dragon", [1]),
    ("Vald", "Ma vie", [1]),
    ("Vald", "Anunnaki", [1]),
    ("Vald", "Rappel", [1]),
    ("Kaaris", "Zoo", [1]),
    ("Kaaris", "Binks", [1]),
    ("Kaaris", "Or Noir", [1]),
    ("Kaaris", "Sombre", [1]),
    ("Kaaris", "2.7 FRMF", [1]),
    ("Kaaris", "Chargé", [1]),
    ("Kaaris", "Pablito", [1]),
    ("Kaaris", "Killé", [1]),
    ("Kaaris", "Tchoin", [1]),
    ("Kaaris", "Double Glock", [1]),
    ("SCH", "Marché noir", [1]),
    ("Maître Gims", "Bella", [2]),
    ("Maître Gims", "J'me tire", [1]),
    ("Maître Gims", "Est-ce que tu m'aimes ?", [2]),
    ("Maître Gims", "Longue vie", [2]),
    ("Keen'V", "J'aimerais trop", [2]),
    ("Keen'V", "Dis-moi oui", [2]),
    ("Keen'V", "La vie du bon côté", [2]),
    ("Keen'V", "Outété", [2]),
    ("Keen'V", "Petite Émilie", [2]),
    ("Keen'V", "Ça va le faire", [2]),
    ("Keen'V", "Rien qu'une fois", [2]),
    ("Keen'V", "Tu me manques", [2]),
    ("Keen'V", "Un monde meilleur", [2]),
    ("Keen'V", "J'aimerais trop (remix)", [2]),
    ("Vitaa", "À fleur de toi", [2]),
    ("Vitaa", "Game Over", [2]),
    ("Vitaa", "Un son pour s'aimer", [2]),
    ("Vitaa", "Ça va ça vient", [2]),
    ("Vitaa", "Avant toi", [2]),
    ("Vitaa", "Je te le donne", [2]),
    ("Slimane", "Viens on s'aime", [2]),
    ("Slimane", "À fleur de peau", [2]),
    ("Slimane", "Chez toi", [2]),
    ("Slimane", "Paname", [2]),
    ("Slimane", "Luna", [2]),
    ("Slimane", "Les roses", [2]),
    ("Slimane", "Avant toi", [2]),
    ("Slimane", "Adieu", [2]),
    ("Amel Bent", "Ma philosophie", [3]),
    ("Amel Bent", "Le droit à l'erreur", [3]),
    ("Amel Bent", "Ne retiens pas tes larmes", [3]),
    ("Amel Bent", "Dis-moi", [3]),
    ("Christophe Maé", "On s'attache", [3]),
    ("Christophe Maé", "Belle demoiselle", [3]),
    ("Christophe Maé", "C'est ma terre", [3]),
    ("Christophe Maé", "Dingue dingue dingue", [3]),
    ("Christophe Maé", "La rumeur", [3]),
    ("Christophe Maé", "Il est où le bonheur", [3]),
    ("Vianney", "Pas là", [3]),
    ("Vianney", "Je m'en vais", [3]),
    ("Vianney", "Dumbo", [3]),
    ("Vianney", "Merci", [3]),
    ("Vianney", "Beau-papa", [3]),
    ("Vianney", "Les filles d'aujourd'hui", [3]),
    ("Angèle", "Balance ton quoi", [3]),
    ("Angèle", "Tout oublier", [3]),
    ("Angèle", "Bruxelles je t'aime", [3]),
    ("Angèle", "Fever", [3]),
    ("Angèle", "Flou", [3]),
    ("Angèle", "La thune", [3]),
    ("Angèle", "Oui ou non", [3]),
    ("Angèle", "Libre", [3]),
    ("Louane", "Avenir", [3]),
    ("Louane", "Jour 1", [3]),
    ("Louane", "Jeune", [3]),
    ("Louane", "On était beau", [3]),
    ("Louane", "Donne-moi ton cœur", [3]),
    ("Zaz", "Je veux", [3]),
    ("Zaz", "On ira", [3]),
    ("Zaz", "Éblouie par la nuit", [3]),
    ("Zaz", "Si", [3]),
    ("Indila", "Dernière danse", [3]),
    ("Indila", "S.O.S", [3]),
    ("Indila", "Tourner dans le vide", [3]),
    ("Indila", "Love Story", [3]),
    ("Indila", "Parle à ta tête", [3]),
    ("Camélia Jordana", "Non non non", [3]),
    ("Camélia Jordana", "Moi c'est", [3]),
    ("Calogero", "En apesanteur", [3]),
    ("Calogero", "Yalla", [3]),
    ("Calogero", "Pomme C", [3]),
    ("Calogero", "Face à la mer", [3]),
    ("Calogero", "Le portrait", [3]),
    ("Jenifer", "J'attends l'amour", [3]),
    ("Jenifer", "Des mots qui résonnent", [3]),
    ("Jenifer", "Comme un hic", [3]),
    ("Jenifer", "Tourner ma page", [3]),
    ("Jenifer", "Sur le fil", [3]),
]

# Vague 2 — artistes demandés + gospel (2026-09-09)
CATALOG_BATCH2: list[tuple[str, str, list[int]]] = [
    # Dena Mwana + gospel FR
    ("Dena Mwana", "Saint Esprit", [9]),
    ("Dena Mwana", "In Extremis", [9]),
    ("Dena Mwana", "Ayebi Ngai", [9]),
    ("Dena Mwana", "L'Eternel est Bon", [9]),
    ("Dena Mwana", "Emmanuel", [9]),
    ("Dena Mwana", "Alléluia", [9]),
    ("Dena Mwana", "Yahweh", [9]),
    ("Dena Mwana", "Louange", [9]),
    ("Sandra Kouame", "Tu es avec moi", [9]),
    ("Sandra Kouame", "Alléluia", [9]),
    ("Dan Luiten", "Tu es ma source", [9]),
    ("Dan Luiten", "Je suis né pour te louer", [9]),
    ("Dan Luiten", "Majesté", [9]),
    ("Dan Luiten", "Toi seul es digne", [9]),
    ("Moise Mbiye", "Molimo", [9]),
    ("Moise Mbiye", "Fidèle", [9]),
    ("Moise Mbiye", "Oza Mosantu", [9]),
    ("Mike Kalambay", "Bisengo ya lola", [9]),
    ("Mike Kalambay", "Esengo Mingi", [9]),
    ("Mike Kalambay", "Le Mariage", [9]),
    # Gospel EN
    ("Sinach", "Way Maker", [9]),
    ("Sinach", "Rejoice", [9]),
    ("Sinach", "Done It Again", [9]),
    ("Sinach", "There's An Overflow", [9]),
    ("Kirk Franklin", "Love Theory", [9]),
    ("Kirk Franklin", "Revolution", [9]),
    ("Kirk Franklin", "Bless Me", [9]),
    ("Kirk Franklin", "I Smile", [9]),
    ("Matt Redman", "10,000 Reasons", [9]),
    ("Matt Redman", "Blessed Be Your Name", [9]),
    ("Matt Redman", "You Never Let Go", [9]),
    ("Hillsong Worship", "Still", [9]),
    ("Hillsong Worship", "What A Beautiful Name", [9]),
    ("Hillsong Worship", "Oceans", [9]),
    ("Hillsong Worship", "Who You Say I Am", [9]),
    ("Hillsong United", "Oceans (Where Feet May Fail)", [9]),
    ("Lauren Daigle", "You Say", [9]),
    ("Lauren Daigle", "Trust In You", [9]),
    ("CeCe Winans", "Goodness of God", [9]),
    ("Elevation Worship", "Graves Into Gardens", [9]),
    # Tayc
    ("Tayc", "N'y pense plus", [2]),
    ("Tayc", "Le temps", [2]),
    ("Tayc", "Dodo", [2]),
    ("Tayc", "Aloviou", [2]),
    ("Tayc", "Palavra", [2]),
    ("Tayc", "C'est lui", [2]),
    ("Tayc", "Forévà", [2]),
    ("Tayc", "Divina", [2]),
    ("Tayc", "Dis-moi", [2]),
    ("Tayc", "Comme toi", [2]),
    ("Tayc", "Moi j'aime trop", [2]),
    ("Tayc", "Sans toi", [2]),
    ("Tayc", "Il te faut", [2]),
    ("Tayc", "Qui", [2]),
    ("Tayc", "Room", [2]),
    # Youssoupha
    ("Youssoupha", "Entourage", [1]),
    ("Youssoupha", "Mon Roi", [1]),
    ("Youssoupha", "Avoir de l'argent", [1]),
    ("Youssoupha", "Devenir vieux", [1]),
    ("Youssoupha", "Faire mieux", [1]),
    ("Youssoupha", "Smile", [1]),
    ("Youssoupha", "Film jaune", [1]),
    ("Youssoupha", "Love européen", [1]),
    ("Youssoupha", "Apprentis philosophes", [1]),
    ("Youssoupha", "Les disques de mon père", [1]),
    ("Youssoupha", "Polynômes", [1]),
    ("Youssoupha", "Dreamin", [1]),
    ("Youssoupha", "Menace du monde", [1]),
    ("Youssoupha", "Histoire vraie", [1]),
    # Sexion d'Assaut
    ("Sexion d'Assaut", "Désolé", [1]),
    ("Sexion d'Assaut", "Wati by Night", [1]),
    ("Sexion d'Assaut", "Avant qu'elle parte", [1]),
    ("Sexion d'Assaut", "Ma direction", [1]),
    ("Sexion d'Assaut", "Africain", [1]),
    ("Sexion d'Assaut", "Balader", [1]),
    ("Sexion d'Assaut", "Cérémonie", [1]),
    ("Sexion d'Assaut", "Pas d'instinct", [1]),
    ("Sexion d'Assaut", "Casquette à l'envers", [1]),
    ("Sexion d'Assaut", "À bout portant", [1]),
    ("Sexion d'Assaut", "L'apéro", [1]),
    ("Sexion d'Assaut", "Paris va bien", [1]),
    ("Sexion d'Assaut", "J'ai pas les words", [1]),
    ("Sexion d'Assaut", "Problèmes d'adultes", [1]),
    # Zaho
    ("Zaho", "C'est chelou", [2]),
    ("Zaho", "Je te promets", [2]),
    ("Zaho", "Allô", [2]),
    ("Zaho", "Un peu beaucoup", [2]),
    ("Zaho", "Kif'n'dir", [2]),
    ("Zaho", "La roue tourne", [2]),
    ("Zaho", "Laissez-les kouma", [2]),
    ("Zaho", "Tourner la page", [2]),
    ("Zaho", "On s'entend plus", [2]),
    ("Zaho", "Comme tous les soirs", [2]),
    # Tiakola
    ("Tiakola", "Meuda", [1]),
    ("Tiakola", "Parapluie", [1]),
    ("Tiakola", "M3lo", [1]),
    ("Tiakola", "Soza", [1]),
    ("Tiakola", "2009", [1]),
    ("Tiakola", "Human Weakness", [1]),
    ("Tiakola", "Gasolina", [1]),
    ("Tiakola", "La claque", [1]),
    ("Tiakola", "Manuel", [1]),
    ("Tiakola", "Pona nini", [1]),
    # Franglish
    ("Franglish", "Candy", [2]),
    ("Franglish", "Position", [2]),
    ("Franglish", "Biberon", [2]),
    ("Franglish", "Petit diamant", [2]),
    ("Franglish", "Trop Parler", [2]),
    ("Franglish", "Sans refrains", [2]),
    ("Franglish", "Clique", [2]),
    ("Franglish", "Don't Digup", [2]),
    ("Franglish", "Côté obscur", [2]),
    ("Franglish", "Mood", [2]),
    ("Franglish", "Béné", [2]),
    ("Franglish", "Fallait pas", [2]),
    # Ed Sheeran
    ("Ed Sheeran", "Shape of You", [5, 4]),
    ("Ed Sheeran", "Perfect", [5, 4]),
    ("Ed Sheeran", "Photograph", [5, 4]),
    ("Ed Sheeran", "Thinking Out Loud", [5, 4]),
    ("Ed Sheeran", "Castle on the Hill", [5, 4]),
    ("Ed Sheeran", "Happier", [5, 4]),
    ("Ed Sheeran", "Bad Habits", [5, 4]),
    ("Ed Sheeran", "Shivers", [5, 4]),
    ("Ed Sheeran", "The A Team", [5, 4]),
    ("Ed Sheeran", "Galway Girl", [5, 4]),
    ("Ed Sheeran", "Beautiful People", [5, 4]),
    ("Ed Sheeran", "I Don't Care", [5, 4]),
    ("Ed Sheeran", "Sing", [5, 4]),
    ("Ed Sheeran", "Don't", [5, 4]),
    ("Ed Sheeran", "Lego House", [5, 4]),
    # Charlotte Dipanda
    ("Charlotte Dipanda", "Coucou", [3, 7]),
    ("Charlotte Dipanda", "On s'en fout", [3, 7]),
    ("Charlotte Dipanda", "Ndolo", [3, 7]),
    ("Charlotte Dipanda", "Elle", [3]),
    ("Charlotte Dipanda", "Sista", [3]),
    ("Charlotte Dipanda", "Bodé", [3]),
    ("Charlotte Dipanda", "Takou", [3]),
    ("Fally Ipupa", "Garde du coeur", [3]),
    # Ben Decca
    ("Ben Decca", "Souffrance d'amour", [3, 7]),
    ("Ben Decca", "O si dibéa", [3, 7]),
    ("Ben Decca", "Na Tondi Oa", [3, 7]),
    ("Ben Decca", "Bonam", [3, 7]),
    ("Ben Decca", "Amour", [3]),
    ("Ben Decca", "Muna", [3]),
    # Belka Tobis (orthographe LRCLIB)
    ("BELKA TOBIS", "WEM NKANA", [7, 3]),
    ("Belka Tobis", "Wem Nkana", [7, 3]),
    # Tom Yom's
    ("Tom Yom's", "Amia", [7, 3]),
    ("Tom Yom's", "Sengato", [7, 3]),
    ("Tom Yoms", "Amia", [7]),
    # Nguea Laroute
    ("Nguea Laroute", "Ebonga Longo", [7, 3]),
    ("Nguea Laroute", "Longue", [7]),
    ("Nguea La Route", "Ebonga Longo", [7]),
]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def pick_lines(lines: list[dict], per_track: int) -> list[str]:
    """Pick diverse punchline candidates from import lyrics_lines."""
    picked: list[str] = []
    seen: set[str] = set()
    # Prefer candidate flag, then length 20–110
    ranked = sorted(
        lines,
        key=lambda L: (
            0 if L.get("candidate") else 1,
            0 if 20 <= len((L.get("text") or "").strip()) <= 110 else 1,
            -len((L.get("text") or "").strip()),
        ),
    )
    for L in ranked:
        text = (L.get("text") or "").strip()
        if not text or len(text) < 18:
            continue
        if re.match(r"^\[.+\]$", text):
            continue
        key = norm(text)
        if len(key) < 10 or key in seen:
            continue
        # skip near-duplicates (prefix)
        if any(key.startswith(s[:40]) or s.startswith(key[:40]) for s in seen if len(s) > 20):
            continue
        seen.add(key)
        picked.append(text)
        if len(picked) >= per_track:
            break
    return picked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.environ.get("API_BASE", "http://127.0.0.1:8084"))
    ap.add_argument("--token", default=os.environ.get("ADMIN_TOKEN", ""))
    ap.add_argument("--target", type=int, default=1000)
    ap.add_argument("--per-track", type=int, default=8)
    ap.add_argument("--sleep", type=float, default=0.35)
    ap.add_argument(
        "--batch",
        choices=["all", "1", "2"],
        default="all",
        help="1=catalogue initial, 2=vague Dena/Tayc/gospel/…, all=concat",
    )
    args = ap.parse_args()

    if not args.token:
        print("ADMIN_TOKEN required", file=sys.stderr)
        return 2

    if args.batch == "1":
        catalog = CATALOG
    elif args.batch == "2":
        catalog = CATALOG_BATCH2
    else:
        catalog = CATALOG + CATALOG_BATCH2

    headers = {"X-Admin-Token": args.token, "Content-Type": "application/json", "Accept": "application/json"}
    client = httpx.Client(base_url=args.base.rstrip("/"), headers=headers, timeout=45.0)

    existing = client.get("/api/music-refs/quotes").json()
    have = {(norm(q["quote"]), norm(q["artist"]), norm(q["title"])) for q in existing}
    count = len(existing)
    print(f"start count={count} catalog={len(catalog)} batch={args.batch} target={args.target}")

    stats = defaultdict(int)
    created_total = 0

    for artist, title, cats in catalog:
        if count + created_total >= args.target:
            break
        try:
            imp = client.post("/api/music-refs/import", json={"artist": artist, "title": title})
        except Exception as e:
            stats["net_err"] += 1
            print(f"ERR net {artist} — {title}: {e}")
            continue
        if imp.status_code == 404:
            stats["miss"] += 1
            print(f"MISS {artist} — {title}")
            time.sleep(args.sleep)
            continue
        if imp.status_code >= 400:
            stats["err"] += 1
            print(f"ERR {imp.status_code} {artist} — {title}: {imp.text[:120]}")
            time.sleep(args.sleep)
            continue

        data = imp.json()
        hints = data.get("hints") or {}
        track = data.get("track") or {}
        a = track.get("artistName") or artist
        t = track.get("trackName") or title
        lines = pick_lines(data.get("lyrics_lines") or [], args.per_track)
        if not lines:
            stats["empty"] += 1
            print(f"EMPTY {a} — {t}")
            time.sleep(args.sleep)
            continue

        payload = []
        for text in lines:
            key = (norm(text), norm(a), norm(t))
            if key in have:
                continue
            have.add(key)
            payload.append(
                {
                    "quote": text,
                    "artist": a,
                    "title": t,
                    "hints": {
                        "year": hints.get("year") or "",
                        "genre": hints.get("genre") or "",
                        "album": hints.get("album") or "",
                        "initials": hints.get("initials") or "",
                    },
                    "category_ids": cats,
                }
            )

        if not payload:
            stats["dup"] += 1
            time.sleep(args.sleep)
            continue

        # chunk inserts (API accepts list)
        res = client.post("/api/music-refs/quotes", json={"quotes": payload})
        if res.status_code >= 400:
            stats["save_err"] += 1
            print(f"SAVE ERR {a} — {t}: {res.status_code} {res.text[:160]}")
        else:
            n = len(res.json())
            created_total += n
            stats["ok"] += 1
            print(f"OK +{n} {a} — {t} (running +{created_total})")
        time.sleep(args.sleep)

    final = client.get("/api/music-refs/quotes").json()
    print("---")
    print(f"final_count={len(final)} created_this_run={created_total} stats={dict(stats)}")
    return 0 if len(final) >= min(args.target, count + 1) or created_total > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
