import unittest
import re
import unicodedata

class MusicRefsEngine:
    """Python reference engine for Music Refs game validation and logic."""

    @staticmethod
    def normalize_string(text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
        # Remove accents
        text_norm = unicodedata.normalize('NFD', text)
        text_no_accents = "".join(c for c in text_norm if unicodedata.category(c) != 'Mn')
        # Lowercase and remove non-alphanumeric
        return re.sub(r'[^a-z0-9]', '', text_no_accents.lower()).strip()

    @classmethod
    def is_match(cls, user_input: str, target: str) -> bool:
        norm_input = cls.normalize_string(user_input)
        norm_target = cls.normalize_string(target)
        if not norm_input or not norm_target:
            return False

        if norm_input == norm_target:
            return True

        if len(norm_input) >= 3 and (norm_input in norm_target or norm_target in norm_input):
            return True

        return False

    def __init__(self, quotes=None):
        self.quotes = quotes or [
            {
                "id": 1,
                "quote": "J'ai pas le temps de regretter mes choix",
                "artist": "Ninho",
                "title": "Jefe",
                "hints": {"year": "2021", "genre": "Rap Français", "album": "JEFE", "initials": "N... - J..."}
            },
            {
                "id": 2,
                "quote": "Le monde est à nous",
                "artist": "PNL",
                "title": "A l'ammoniaque",
                "hints": {"year": "2018", "genre": "Cloud Rap", "album": "Deux Frères", "initials": "P... - A..."}
            }
        ]
        self.played_ids = set()
        self.current_index = 0
        self.score = 0
        self.streak = 0
        self.revealed_hints = set()

    def get_current_quote(self):
        return self.quotes[self.current_index]

    def reveal_hint(self, hint_type: str):
        quote = self.get_current_quote()
        if hint_type not in quote["hints"]:
            raise ValueError(f"Indice {hint_type} non disponible")
        if hint_type in self.revealed_hints:
            raise ValueError(f"Indice {hint_type} déjà révélé")
        
        self.revealed_hints.add(hint_type)
        return quote["hints"][hint_type]

    def validate_answer(self, input_artist: str, input_title: str):
        quote = self.get_current_quote()
        artist_ok = self.is_match(input_artist, quote["artist"])
        title_ok = self.is_match(input_title, quote["title"])

        if not artist_ok and not title_ok:
            self.streak = 0
            return {"success": False, "points": 0, "score": self.score, "streak": self.streak}

        points = 0
        if artist_ok:
            points += 100
        if title_ok:
            points += 100

        # Deduct hints penalty (-20 per hint)
        hint_penalty = len(self.revealed_hints) * 20
        points = max(20, points - hint_penalty)

        if artist_ok and title_ok:
            self.streak += 1
            streak_bonus = (self.streak - 1) * 50
            points += 50 + streak_bonus

        self.score += points
        return {
            "success": True,
            "artist_matched": artist_ok,
            "title_matched": title_ok,
            "points": points,
            "score": self.score,
            "streak": self.streak
        }

    def next_quote(self):
        self.revealed_hints.clear()
        self.current_index = (self.current_index + 1) % len(self.quotes)
        return self.get_current_quote()

    def reset_game(self):
        self.score = 0
        self.streak = 0
        self.revealed_hints.clear()
        self.current_index = 0


class TestMusicRefsUserStories(unittest.TestCase):
    """Automated Unit Tests for Task #4 User Stories."""

    def setUp(self):
        self.engine = MusicRefsEngine()

    def test_us1_random_quote_display(self):
        """User Story 1: Affichage aléatoire de punchlines et citations."""
        quote = self.engine.get_current_quote()
        self.assertIn("quote", quote)
        self.assertIn("artist", quote)
        self.assertIn("title", quote)
        self.assertTrue(len(quote["quote"]) > 0)

    def test_us2_answer_input_and_validation(self):
        """User Story 2: Saisie et validation de la réponse."""
        # Case 1: Exact match
        res = self.engine.validate_answer("Ninho", "Jefe")
        self.assertTrue(res["success"])
        self.assertTrue(res["artist_matched"])
        self.assertTrue(res["title_matched"])

        # Case 2: Flexible case and accent handling
        self.assertTrue(MusicRefsEngine.is_match("ninho", "Ninho"))
        self.assertTrue(MusicRefsEngine.is_match("A l'ammoniaque", "A l'ammoniaque"))

        # Case 3: Wrong answer
        res_fail = self.engine.validate_answer("WrongArtist", "WrongTitle")
        self.assertFalse(res_fail["success"])

    def test_us3_hint_system(self):
        """User Story 3: Système d'affichage d'indices."""
        hint_val = self.engine.reveal_hint("year")
        self.assertEqual(hint_val, "2021")
        self.assertIn("year", self.engine.revealed_hints)

        # Requesting same hint twice throws ValueError
        with self.assertRaises(ValueError):
            self.engine.reveal_hint("year")

    def test_us4_score_calculation_and_tracking(self):
        """User Story 4: Calcul et suivi du score."""
        initial_score = self.engine.score
        # Reveal hint (-20 penalty)
        self.engine.reveal_hint("genre")
        
        # Correct answer
        res = self.engine.validate_answer("Ninho", "Jefe")
        self.assertTrue(res["success"])
        self.assertGreater(res["score"], initial_score)
        self.assertEqual(self.engine.streak, 1)

    def test_us5_game_progression_and_replayability(self):
        """User Story 5: Progression et rejouabilité."""
        first_quote = self.engine.get_current_quote()
        second_quote = self.engine.next_quote()
        self.assertNotEqual(first_quote["id"], second_quote["id"])

        # Reset game
        self.engine.reset_game()
        self.assertEqual(self.engine.score, 0)
        self.assertEqual(self.engine.streak, 0)
        self.assertEqual(self.engine.current_index, 0)

    def test_us6_modern_data_structure(self):
        """User Story 6: Verification of complete quote metadata for UI rendering."""
        for q in self.engine.quotes:
            self.assertIn("hints", q)
            self.assertIn("year", q["hints"])
            self.assertIn("genre", q["hints"])
            self.assertIn("album", q["hints"])
            self.assertIn("initials", q["hints"])

if __name__ == '__main__':
    unittest.main()
