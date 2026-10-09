"""Offline regression tests for GhostTrack's original and enhanced features."""

import contextlib
import io
import json
import unittest
from unittest.mock import patch

import requests

from ghosttrack import cli, services
from ghosttrack.platforms import PROFILES


class IPTests(unittest.TestCase):
    def test_ipv4_and_exact_maps(self):
        payload = {
            "success": True,
            "type": "IPv4",
            "latitude": 3.139003,
            "longitude": 101.686855,
            "country": "Malaysia",
            "flag": {"emoji": "🇲🇾"},
            "connection": {"isp": "Test ISP", "asn": 123},
            "timezone": {"id": "Asia/Kuala_Lumpur"},
        }
        with patch.object(services, "get_json", return_value=payload) as get:
            result = services.ip_lookup(" 8.8.8.8 ")
        self.assertEqual(result["ip"], "8.8.8.8")
        self.assertEqual(result["country"], "Malaysia")
        self.assertEqual(result["map_url"], "https://www.google.com/maps/search/?api=1&query=3.139003%2C101.686855")
        self.assertEqual(result["connection"]["isp"], "Test ISP")
        self.assertEqual(get.call_args.args[0], "https://ipwho.is/8.8.8.8")

    def test_ipv6(self):
        with patch.object(services, "get_json", return_value={"success": True}) as get:
            self.assertEqual(services.ip_lookup("2606:4700:4700::1111")["type"], None)
        self.assertIn("2606:4700:4700::1111", get.call_args.args[0])

    def test_private_and_local_addresses_rejected(self):
        for address in ["127.0.0.1", "10.0.0.1", "192.168.1.2", "::1", "not-an-ip"]:
            with self.subTest(address=address), patch.object(services, "get_json") as get:
                with self.assertRaises(services.LookupError):
                    services.ip_lookup(address)
                get.assert_not_called()

    def test_api_error(self):
        with patch.object(services, "get_json", return_value={"success": False, "message": "invalid query"}):
            with self.assertRaisesRegex(services.LookupError, "invalid query"):
                services.ip_lookup("8.8.8.8")

    def test_bad_nested_payload(self):
        with patch.object(services, "get_json", return_value={"connection": "bad"}):
            with self.assertRaisesRegex(services.LookupError, "unexpected data format"):
                services.ip_lookup("8.8.8.8")

    def test_missing_fields_are_safe(self):
        with patch.object(services, "get_json", return_value={"success": True}):
            self.assertIsNone(services.ip_lookup("1.1.1.1")["map_url"])


class NetworkTests(unittest.TestCase):
    def test_tls_and_timeout_enforced(self):
        reply = unittest.mock.Mock()
        reply.json.return_value = {"ip": "1.1.1.1"}
        with patch.object(services.requests, "get", return_value=reply) as get:
            self.assertEqual(services.my_ip()["ip"], "1.1.1.1")
        args, kwargs = get.call_args
        self.assertTrue(args[0].startswith("https://"))
        self.assertGreater(kwargs["timeout"], 0)
        reply.raise_for_status.assert_called_once()

    def test_timeout_is_recoverable(self):
        with patch.object(services.requests, "get", side_effect=requests.Timeout):
            with self.assertRaisesRegex(services.LookupError, "timed out"):
                services.my_ip()

    def test_network_error_is_recoverable(self):
        with patch.object(services.requests, "get", side_effect=requests.ConnectionError("offline")):
            with self.assertRaises(services.LookupError):
                services.my_ip()

    def test_invalid_my_ip_payload(self):
        with patch.object(services, "get_json", return_value={"ip": "not-an-ip"}):
            with self.assertRaises(services.LookupError):
                services.my_ip()

    def test_invalid_json(self):
        reply = unittest.mock.Mock()
        reply.json.side_effect = ValueError("bad JSON")
        with patch.object(services.requests, "get", return_value=reply):
            with self.assertRaises(services.LookupError):
                services.my_ip()


class PhoneTests(unittest.TestCase):
    def test_valid_international_number(self):
        result = services.phone_lookup("+14155552671", region="MY")
        self.assertTrue(result["possible"])
        self.assertTrue(result["valid"])
        self.assertEqual(result["region"], "US")
        self.assertEqual(result["e164"], "+14155552671")
        self.assertIn("live location", result["note"])

    def test_local_default_region(self):
        result = services.phone_lookup("4155552671", region="US")
        self.assertEqual(result["e164"], "+14155552671")

    def test_bad_region(self):
        for region in ["", "malaysia", "12", "US/../", "💀"]:
            with self.subTest(region=region):
                with self.assertRaises(services.LookupError):
                    services.phone_lookup("+14155552671", region=region)

    def test_bad_number(self):
        with self.assertRaises(services.LookupError):
            services.phone_lookup("invalid-phone", region="MY")


class UsernameTests(unittest.TestCase):
    def test_only_active_curated_platforms(self):
        self.assertGreaterEqual(len(PROFILES), 10)
        names = [name for name, _ in PROFILES]
        self.assertEqual(len(names), len(set(names)))
        for removed in ("Ello", "StumbleUpon", "Periscope"):
            self.assertNotIn(removed, names)

    def test_unverified_by_default_for_non_api_platforms(self):
        with patch.object(services, "_github_status", return_value=("found", "verified")), \
             patch.object(services, "_gitlab_status", return_value=("not_found", "verified")):
            data = services.username_lookup("example")
        self.assertEqual(data["profiles"][0]["status"], "found")
        self.assertEqual(data["profiles"][1]["status"], "not_found")
        self.assertTrue(all(p["status"] == "unverified" for p in data["profiles"][2:]))
        self.assertTrue(all(p["url"].startswith("https://") for p in data["profiles"]))

    def test_no_check_offline(self):
        with patch.object(services, "get_json") as get:
            data = services.username_lookup("octocat", check=False)
            self.assertTrue(all(p["status"] == "unverified" for p in data["profiles"]))
        get.assert_not_called()

    def test_username_validation(self):
        for username in ["", ".", "..", "../etc/passwd", "foo/bar", "a"*40, "hello?x", "a b"]:
            with self.subTest(username=username):
                with self.assertRaises(services.LookupError):
                    services.username_lookup(username, check=False)

    def test_github_found(self):
        with patch.object(services, "get_json", return_value={"login": "Octocat"}):
            self.assertEqual(services._github_status("octocat", timeout=3)[0], "found")

    def test_github_404_not_found(self):
        response = requests.Response()
        response.status_code = 404
        exc = requests.HTTPError("404", response=response)
        with patch.object(services, "get_json", side_effect=services.LookupError("404")) as get:
            def failing(*args, **kwargs):
                try:
                    raise exc
                except requests.HTTPError as cause:
                    raise services.LookupError("404") from cause
            get.side_effect = failing
            self.assertEqual(services._github_status("missing", timeout=3)[0], "not_found")

    def test_github_403_never_not_found(self):
        response = requests.Response()
        response.status_code = 403
        def failing(*args, **kwargs):
            try:
                raise requests.HTTPError("403", response=response)
            except requests.HTTPError as cause:
                raise services.LookupError("403") from cause
        with patch.object(services, "get_json", side_effect=failing):
            self.assertEqual(services._github_status("octocat", timeout=3)[0], "unverified")

    def test_gitlab_match_and_empty(self):
        with patch.object(services, "get_json", return_value=[{"username": "Example"}]):
            self.assertEqual(services._gitlab_status("example", timeout=3)[0], "found")
        with patch.object(services, "get_json", return_value=[]):
            self.assertEqual(services._gitlab_status("example", timeout=3)[0], "not_found")
        with patch.object(services, "get_json", return_value={"wrong": "shape"}):
            self.assertEqual(services._gitlab_status("example", timeout=3)[0], "unverified")


class CLITests(unittest.TestCase):
    def test_original_menu_options_preserved(self):
        with patch("builtins.input", side_effect=["0"]), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main([]), 0)
        for option in ("IP Tracker", "Show Your IP", "Phone Number Tracker", "Username Tracker"):
            self.assertIn(option, out.getvalue())

    def test_interactive_invalid_choice_recovers(self):
        with patch("builtins.input", side_effect=["9", "0"]), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main([]), 0)
        self.assertIn("Choose 0, 1, 2, 3, or 4", out.getvalue())

    def test_cli_json_subcommand(self):
        with patch.object(cli, "run", return_value={"ip": "8.8.8.8"}), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(["ip", "8.8.8.8", "--json"]), 0)
        self.assertEqual(json.loads(out.getvalue()), {"ip": "8.8.8.8"})

    def test_cli_json_global_flag(self):
        with patch.object(cli, "run", return_value={"ip": "8.8.8.8"}), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(["--json", "ip", "8.8.8.8"]), 0)
        self.assertEqual(json.loads(out.getvalue()), {"ip": "8.8.8.8"})

    def test_cli_error_json(self):
        with patch.object(cli, "run", side_effect=services.LookupError("offline")), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(["my-ip", "--json"]), 1)
        self.assertEqual(json.loads(out.getvalue()), {"error": "offline"})

    def test_phone_region_option(self):
        with patch.object(cli, "run", return_value={}) as run, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["phone", "+14155552671", "--region", "US"]), 0)
        self.assertEqual(run.call_args.kwargs["region"], "US")

    def test_no_check_option(self):
        with patch.object(cli, "run", return_value={}) as run, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["username", "octocat", "--no-check"]), 0)
        self.assertIs(run.call_args.kwargs["check"], False)


if __name__ == "__main__":
    unittest.main()
