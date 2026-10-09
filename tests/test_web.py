"""Integration checks for the isolated FastAPI interfaces (no outbound calls)."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from ghosttrack.web.api import create_app
from ghosttrack.web.auth import AdminAuth, hash_password, verify_password
from ghosttrack.web.state import RateLimiter, Store


class WebIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        self.db = str(root / "storage" / "ghosttrack.db")
        secrets = root / "private"
        secrets.mkdir()
        (secrets / "admin_password_hash").write_text(hash_password("very-long-test-password-123"))
        (secrets / "session_secret").write_text("testing-session-secret-" + "a" * 50)
        self.admin = TestClient(create_app("admin", database=self.db, secret_dir=str(secrets),
                                           secure_cookie=False, login_limit=5))
        self.public = TestClient(create_app("public", database=self.db, public_limit=2))
        self.admin.__enter__()
        self.public.__enter__()

    def tearDown(self):
        self.public.__exit__(None, None, None)
        self.admin.__exit__(None, None, None)
        self.tempdir.cleanup()

    @staticmethod
    def post(client, path, body, csrf=None):
        headers = {"X-GhostTrack-UI": "1"}
        if csrf is not None:
            headers["X-CSRF-Token"] = csrf
        return client.post(path, json=body, headers=headers)

    def login(self):
        response = self.post(self.admin, "/api/admin/login",
                             {"password": "very-long-test-password-123"})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["csrf"]

    def test_admin_secret_setup_and_hash(self):
        hashed = hash_password("very-long-test-password-123")
        self.assertTrue(verify_password("very-long-test-password-123", hashed))
        self.assertFalse(verify_password("wrong", hashed))
        self.assertFalse(verify_password("anything", "bad-hash"))
        with self.assertRaises(ValueError):
            hash_password("short")

    def test_default_disabled_and_no_admin_on_public_port(self):
        public = self.public.get("/api/status")
        self.assertEqual(public.status_code, 200)
        self.assertFalse(public.json()["public_enabled"])
        self.assertEqual(self.public.get("/api/admin/me").status_code, 404)
        self.assertEqual(self.public.get("/api/admin/summary").status_code, 404)
        self.assertEqual(self.public.post("/api/admin/public-access", json={"enabled": True}).status_code, 403)
        self.assertEqual(self.post(self.public, "/api/lookup/ip", {"value": "8.8.8.8"}).status_code, 503)

    def test_public_html_and_admin_html_are_separate(self):
        public = self.public.get("/")
        private = self.admin.get("/")
        self.assertEqual(public.status_code, 200)
        self.assertEqual(private.status_code, 200)
        self.assertIn("PUBLIC WORKSPACE", public.text)
        self.assertNotIn("PRIVATE CONTROL PLANE", public.text)
        self.assertIn("PRIVATE CONTROL PLANE", private.text)
        self.assertNotIn("PUBLIC WORKSPACE", private.text)
        self.assertIn("frame-ancestors 'none'", public.headers["content-security-policy"])
        for route in ("/assets/style.css", "/assets/app.js"):
            self.assertEqual(self.public.get(route).status_code, 200)
            self.assertEqual(self.admin.get(route).status_code, 200)

    def test_login_auth_and_csrf_required(self):
        self.assertEqual(self.admin.get("/api/admin/me").status_code, 401)
        self.assertEqual(self.post(self.admin, "/api/admin/login", {"password": "wrong"}).status_code, 401)
        csrf = self.login()
        self.assertTrue(self.admin.get("/api/admin/me").json()["authenticated"])
        self.assertEqual(self.post(self.admin, "/api/admin/public-access", {"enabled": True}).status_code, 403)
        self.assertEqual(self.post(self.admin, "/api/admin/public-access",
                                   {"enabled": True}, csrf="bogus").status_code, 403)
        response = self.post(self.admin, "/api/admin/public-access", {"enabled": True}, csrf=csrf)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["public_enabled"])

    def test_public_toggle_and_shared_db(self):
        csrf = self.login()
        self.assertFalse(self.public.get("/api/status").json()["public_enabled"])
        self.post(self.admin, "/api/admin/public-access", {"enabled": True}, csrf)
        self.assertTrue(self.public.get("/api/status").json()["public_enabled"])
        with patch("ghosttrack.web.api.ip_lookup", return_value={"country": "Example"}):
            result = self.post(self.public, "/api/lookup/ip", {"value": "8.8.8.8"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["result"]["country"], "Example")
        summary = self.admin.get("/api/admin/summary")
        self.assertEqual(summary.status_code, 200)
        counts = summary.json()["counts"]
        self.assertTrue(any(x["interface"] == "public" and x["tool"] == "ip"
                            and x["outcome"] == "success" for x in counts))
        self.assertFalse(any("value" in record or "visitor" in record for record in counts))
        self.post(self.admin, "/api/admin/public-access", {"enabled": False}, csrf)
        self.assertEqual(self.post(self.public, "/api/lookup/ip", {"value": "8.8.8.8"}).status_code, 503)

    def test_admin_private_lookups_and_no_csrf_leak(self):
        csrf = self.login()
        with patch("ghosttrack.web.api.my_ip", return_value={"ip": "203.0.113.3"}):
            result = self.post(self.admin, "/api/lookup/my-ip", {"value": "-"}, csrf)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["result"]["ip"], "203.0.113.3")
        self.assertEqual(self.post(self.public, "/api/lookup/my-ip", {"value": "-"}).status_code, 404)

    def test_no_form_or_cross_site_post(self):
        self.assertEqual(self.admin.post("/api/admin/login",
                                         json={"password": "very-long-test-password-123"}).status_code, 403)
        self.assertEqual(self.public.post("/api/lookup/ip",
                                          json={"value": "8.8.8.8"}).status_code, 403)

    def test_invalid_payload_and_public_rate_limit(self):
        csrf = self.login()
        self.post(self.admin, "/api/admin/public-access", {"enabled": True}, csrf)
        with patch("ghosttrack.web.api.ip_lookup", return_value={"ip": "8.8.8.8"}):
            self.assertEqual(self.post(self.public, "/api/lookup/ip",
                                       {"value": "8.8.8.8", "unexpected": "a"}).status_code, 422)
            self.assertEqual(self.post(self.public, "/api/lookup/ip",
                                       {"value": "8.8.8.8"}).status_code, 200)
            self.assertEqual(self.post(self.public, "/api/lookup/ip",
                                       {"value": "8.8.8.8"}).status_code, 200)
            self.assertEqual(self.post(self.public, "/api/lookup/ip",
                                       {"value": "8.8.8.8"}).status_code, 429)

    def test_login_limit_and_session_logout(self):
        for _ in range(5):
            self.assertEqual(self.post(self.admin, "/api/admin/login",
                                       {"password": "nope"}).status_code, 401)
        self.assertEqual(self.post(self.admin, "/api/admin/login",
                                   {"password": "very-long-test-password-123"}).status_code, 429)

    def test_logout_removes_browser_session(self):
        csrf = self.login()
        response = self.post(self.admin, "/api/admin/logout", {}, csrf)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.admin.get("/api/admin/me").status_code, 401)

    def test_admin_bad_secrets_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileNotFoundError):
                create_app("admin", database=self.db, secret_dir=temp)

    def test_health_and_unknown_tools(self):
        self.assertEqual(self.public.get("/healthz").json()["interface"], "public")
        self.assertEqual(self.post(self.public, "/api/lookup/delete", {"value": "x"}).status_code, 404)


class StateUnitTests(unittest.TestCase):
    def test_rate_limiter_different_clients(self):
        limiter = RateLimiter(limit=2, window=60)
        self.assertTrue(limiter.allow("one"))
        self.assertTrue(limiter.allow("one"))
        self.assertFalse(limiter.allow("one"))
        self.assertTrue(limiter.allow("two"))

    def test_rate_limiter_bounded_clients(self):
        limiter = RateLimiter(limit=2, window=60, max_clients=1)
        self.assertTrue(limiter.allow("first"))
        self.assertFalse(limiter.allow("second"))
        self.assertEqual(len(limiter.clients), 1)

    def test_sqlite_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(str(Path(temp) / "nonexistent.db"))
            self.assertFalse(store.public_enabled())
            store.initialize()
            self.assertFalse(store.public_enabled())
            store.set_public_enabled(True)
            self.assertTrue(store.public_enabled())


if __name__ == "__main__":
    unittest.main()
