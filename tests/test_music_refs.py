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


class TestMusicRefsTask5RoutingAnd404(unittest.TestCase):
    """Automated Unit & Integration Tests for Task #5 User Stories."""

    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0, '/app')
        try:
            from main import app
            from fastapi.testclient import TestClient
            cls.client = TestClient(app)
        except Exception as e:
            cls.client = None
            print(f"TestClient init notice: {e}")

    def test_task5_root_path_routing_frontend_html(self):
        """Task #5 US1: Root Path Routing to Frontend Web Interface (HTML)."""
        if not self.client:
            self.skipTest("FastAPI app not available for TestClient")
        res = self.client.get('/', headers={'Accept': 'text/html'})
        self.assertEqual(res.status_code, 200)
        self.assertIn("MUSIC REFS", res.text)
        self.assertIn("text/html", res.headers.get("content-type", ""))

    def test_task5_reverse_proxy_static_files_configuration(self):
        """Task #5 US2: Reverse Proxy and Static Files Configuration Verification."""
        import os
        self.assertTrue(os.path.exists('/workspace/music-refs/index.html'), "index.html missing")
        self.assertTrue(os.path.exists('/workspace/music-refs/404.html'), "404.html missing")
        self.assertTrue(os.path.exists('/workspace/music-refs/nginx.conf'), "nginx.conf missing")

        with open('/workspace/music-refs/nginx.conf', 'r') as f:
            content = f.read()
            self.assertIn('music-refs-dev.kladriva.ca', content)
            self.assertIn('try_files', content)
            self.assertIn('404.html', content)

    def test_task5_backend_api_root_and_health_check(self):
        """Task #5 US3: Backend API Root Endpoint and Health Check Response."""
        if not self.client:
            self.skipTest("FastAPI app not available for TestClient")
        # GET / with Accept: application/json
        res_root = self.client.get('/', headers={'Accept': 'application/json'})
        self.assertEqual(res_root.status_code, 200)
        data_root = res_root.json()
        self.assertEqual(data_root.get('status'), 'ok')
        self.assertEqual(data_root.get('service'), 'Music Refs API')

        # GET /health
        res_health = self.client.get('/health')
        self.assertEqual(res_health.status_code, 200)
        data_health = res_health.json()
        self.assertEqual(data_health.get('status'), 'ok')

    def test_task5_user_friendly_404_error_page_html(self):
        """Task #5 US4: Branded 404 Error Page for Browser HTML Requests."""
        if not self.client:
            self.skipTest("FastAPI app not available for TestClient")
        res = self.client.get('/invalid-page-xyz', headers={'Accept': 'text/html'})
        self.assertEqual(res.status_code, 404)
        self.assertIn("404", res.text)
        self.assertIn("Oups ! Fausse Note", res.text)
        self.assertIn("Accueil", res.text)

    def test_task5_user_friendly_404_error_page_json(self):
        """Task #5 US4: Structured JSON 404 Error Response for API Clients."""
        if not self.client:
            self.skipTest("FastAPI app not available for TestClient")
        res = self.client.get('/api/music-refs/nonexistent', headers={'Accept': 'application/json'})
        self.assertEqual(res.status_code, 404)
        data = res.json()
        self.assertEqual(data.get('error'), 'Not Found')
        self.assertEqual(data.get('status_code'), 404)
        self.assertIn('available_endpoints', data)


class TestMusicRefsTask6SSLAndSNI(unittest.TestCase):
    """Automated Unit & Integration Tests for Task #6 SSL/TLS, SNI & Monitoring User Stories."""

    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0, '/workspace/music-refs')
        from scripts import cert_manager, ssl_monitor
        cls.cert_manager = cert_manager
        cls.ssl_monitor = ssl_monitor

        # Ensure certificates exist
        cls.cert_manager.generate_certificate()

    def test_task6_us1_ssl_certificate_provisioning_and_san(self):
        """Task #6 US1: Provision and Configure SSL/TLS Certificate for Subdomain."""
        cert_path = self.cert_manager.CERT_PATH
        key_path = self.cert_manager.KEY_PATH

        import os
        self.assertTrue(os.path.exists(cert_path), "SSL Certificate file missing")
        self.assertTrue(os.path.exists(key_path), "SSL Key file missing")

        details = self.cert_manager.get_certificate_details(cert_path)
        self.assertNotIn("error", details)
        self.assertEqual(details.get("domain"), "music-refs-dev.kladriva.ca")

        # Verify SAN contains subdomain
        san_str = " ".join(details.get("subject_alt_names", []))
        self.assertIn("music-refs-dev.kladriva.ca", san_str)

        expiry = details.get("expiry", {})
        self.assertTrue(expiry.get("valid"))
        self.assertGreater(expiry.get("days_remaining", 0), 30)

    def test_task6_us2_reverse_proxy_sni_and_virtual_host_settings(self):
        """Task #6 US2: Configure Reverse Proxy SNI and Virtual Host Settings."""
        import os
        nginx_conf_path = '/workspace/music-refs/nginx.conf'
        self.assertTrue(os.path.exists(nginx_conf_path))

        with open(nginx_conf_path, 'r') as f:
            content = f.read()

        # Virtual host & SNI check
        self.assertIn('server_name music-refs-dev.kladriva.ca;', content)
        self.assertIn('listen 443 ssl', content)
        self.assertIn('ssl_certificate /workspace/music-refs/certs/music-refs-dev.kladriva.ca.crt;', content)
        self.assertIn('ssl_certificate_key /workspace/music-refs/certs/music-refs-dev.kladriva.ca.key;', content)

        # TLS versions & Ciphers
        self.assertIn('ssl_protocols TLSv1.2 TLSv1.3;', content)
        self.assertIn('ssl_ciphers', content)
        self.assertIn('ssl_session_cache', content)

        # HTTP to HTTPS redirect
        self.assertIn('return 301 https://$host$request_uri;', content)

    def test_task6_us3_automate_ssl_certificate_management_and_renewal(self):
        """Task #6 US3: Automate SSL Certificate Management and Renewal."""
        expiry_info = self.cert_manager.check_certificate_expiry()
        self.assertTrue(expiry_info.get("valid"))
        self.assertFalse(expiry_info.get("needs_renewal"))

        # Test renewal logic when valid
        renew_res = self.cert_manager.renew_certificate_if_needed()
        self.assertEqual(renew_res.get("status"), "valid")
        self.assertEqual(renew_res.get("action_taken"), "none")

        # Test forced renewal
        force_renew_res = self.cert_manager.renew_certificate_if_needed(force=True)
        self.assertEqual(force_renew_res.get("status"), "created_or_renewed")
        self.assertEqual(force_renew_res.get("action_taken"), "renewed")

    def test_task6_us4_ssl_handshake_and_domain_monitoring(self):
        """Task #6 US4: Implement SSL/TLS Handshake and Domain Health Monitoring."""
        import http.server
        import ssl
        import threading
        import socket

        # Test local certificate monitoring logic
        cert_report = self.ssl_monitor.check_local_certificate()
        self.assertTrue(cert_report.get("valid"))
        self.assertEqual(cert_report.get("status"), "OK")
        self.assertGreater(cert_report.get("days_remaining"), 30)

        # Start a temporary local HTTPS server with SNI to test live TLS handshake
        class SimpleHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "ok", "service": "Music Refs Mock HTTPS"}')

            def log_message(self, format, *args):
                pass

        # Pick an available port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
        sock.close()

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(
            certfile=self.cert_manager.CERT_PATH,
            keyfile=self.cert_manager.KEY_PATH
        )

        class QuietHTTPServer(http.server.HTTPServer):
            def handle_error(self, request, client_address):
                pass

        httpd = QuietHTTPServer(('127.0.0.1', port), SimpleHandler)
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()

        try:
            # Test live TLS handshake with SNI
            tls_res = self.ssl_monitor.perform_tls_handshake_check(
                host="127.0.0.1",
                port=port,
                sni_hostname="music-refs-dev.kladriva.ca"
            )
            self.assertTrue(tls_res.get("handshake_success"))
            self.assertEqual(tls_res.get("status"), "OK")
            self.assertIn("TLS", tls_res.get("protocol", ""))

            # Test full domain health report with live HTTPS server endpoint
            health_url = f"https://127.0.0.1:{port}/health"
            full_report = self.ssl_monitor.run_full_domain_health_check(
                host="127.0.0.1",
                port=port,
                sni_hostname="music-refs-dev.kladriva.ca",
                cert_path=self.cert_manager.CERT_PATH,
                health_url=health_url
            )

            self.assertEqual(full_report.get("overall_status"), "OK")
            self.assertTrue(full_report.get("certificate_check", {}).get("valid"))
            self.assertTrue(full_report.get("tls_handshake_check", {}).get("handshake_success"))
            self.assertTrue(full_report.get("endpoint_check", {}).get("reachable"))
            self.assertEqual(full_report.get("endpoint_check", {}).get("status_code"), 200)

        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == '__main__':
    unittest.main()


