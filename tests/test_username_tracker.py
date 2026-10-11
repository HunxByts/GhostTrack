import unittest
from unittest.mock import patch, MagicMock
import requests

class TestUsernameTracker(unittest.TestCase):
    def test_import_module(self):
        # Must be able to import the module and functions
        import username_tracker
        self.assertTrue(hasattr(username_tracker, 'check_site'))
        self.assertTrue(hasattr(username_tracker, 'search_username'))
        self.assertTrue(hasattr(username_tracker, 'DEFAULT_SITES'))

    @patch('requests.get')
    def test_check_site_found(self, mock_get):
        import username_tracker
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        site = {"url": "https://example.com/{}", "name": "Example"}
        res = username_tracker.check_site(site, "testuser", timeout=2)

        self.assertEqual(res['name'], 'Example')
        self.assertEqual(res['status'], 'FOUND')
        self.assertEqual(res['url'], 'https://example.com/testuser')
        self.assertIn('Found', res['message'])

    @patch('requests.get')
    def test_check_site_not_found(self, mock_get):
        import username_tracker
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        site = {"url": "https://example.com/{}", "name": "Example"}
        res = username_tracker.check_site(site, "testuser", timeout=2)

        self.assertEqual(res['name'], 'Example')
        self.assertEqual(res['status'], 'NOT_FOUND')
        self.assertIn('not found', res['message'].lower())

    @patch('requests.get')
    def test_check_site_timeout(self, mock_get):
        import username_tracker
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        site = {"url": "https://example.com/{}", "name": "Example"}
        # Must not raise an exception
        res = username_tracker.check_site(site, "testuser", timeout=2)

        self.assertEqual(res['name'], 'Example')
        self.assertEqual(res['status'], 'TIMEOUT')
        self.assertIn('timed out', res['message'].lower())

    @patch('requests.get')
    def test_check_site_connection_error(self, mock_get):
        import username_tracker
        mock_get.side_effect = requests.exceptions.ConnectionError("DNS failure")

        site = {"url": "https://example.com/{}", "name": "Example"}
        # Must not raise an exception
        res = username_tracker.check_site(site, "testuser", timeout=2)

        self.assertEqual(res['name'], 'Example')
        self.assertEqual(res['status'], 'ERROR')
        self.assertIn('connection error', res['message'].lower())

    @patch('requests.get')
    def test_check_site_blocked_or_rate_limited(self, mock_get):
        import username_tracker
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        site = {"url": "https://example.com/{}", "name": "Example"}
        res = username_tracker.check_site(site, "testuser", timeout=2)

        self.assertEqual(res['name'], 'Example')
        self.assertEqual(res['status'], 'BLOCKED')

    @patch('requests.get')
    def test_search_username_resilience(self, mock_get):
        """Test that when one site fails/times out, other sites still return their result."""
        import username_tracker

        def side_effect(url, **kwargs):
            if 'site1' in url:
                raise requests.exceptions.Timeout("Site 1 unresponsive")
            elif 'site2' in url:
                resp = MagicMock()
                resp.status_code = 200
                return resp
            else:
                resp = MagicMock()
                resp.status_code = 404
                return resp

        mock_get.side_effect = side_effect

        test_sites = [
            {"url": "https://site1.com/{}", "name": "Site1"},
            {"url": "https://site2.com/{}", "name": "Site2"},
            {"url": "https://site3.com/{}", "name": "Site3"}
        ]

        results = username_tracker.search_username("target", sites=test_sites)

        # All 3 sites must have results returned
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]['status'], 'TIMEOUT')
        self.assertEqual(results[1]['status'], 'FOUND')
        self.assertEqual(results[2]['status'], 'NOT_FOUND')

    @patch('requests.get')
    def test_regex_check_rejection(self, mock_get):
        """Should reject invalid username formats before sending network requests."""
        import username_tracker
        site = {
            "name": "Twitter",
            "url": "https://x.com/{}",
            "regex": r"^[a-zA-Z0-9_]{1,15}$"
        }
        # More than 15 chars - invalid on Twitter
        res = username_tracker.check_site(site, "this_username_is_way_too_long_for_twitter")
        self.assertEqual(res['status'], 'NOT_FOUND')
        self.assertIn("format", res['message'].lower())
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_missing_string_detection(self, mock_get):
        """Should mark as NOT_FOUND if response contains any error_msg/m_string even with HTTP 200."""
        import username_tracker
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><meta name="robots" content="noindex, nofollow"></html>'
        mock_response.url = 'https://t.me/fakeuser'
        mock_get.return_value = mock_response

        site = {
            "name": "Telegram",
            "url": "https://t.me/{}",
            "m_string": ["noindex, nofollow"]
        }
        res = username_tracker.check_site(site, "fakeuser")
        self.assertEqual(res['status'], 'NOT_FOUND')

    @patch('requests.get')
    def test_existence_string_detection(self, mock_get):
        """Should mark as FOUND only if e_string is present in response body."""
        import username_tracker
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><title>Profile | Pinterest</title><body>Welcome to Pinterest</body></html>'
        mock_response.url = 'https://www.pinterest.com/fakeuser/'
        mock_get.return_value = mock_response

        site = {
            "name": "Pinterest",
            "url": "https://www.pinterest.com/{}/",
            "e_string": " - Profile | Pinterest"
        }
        # Does not match exact ' - Profile | Pinterest'
        res = username_tracker.check_site(site, "fakeuser")
        self.assertEqual(res['status'], 'NOT_FOUND')

        # Now test with e_string present
        mock_response.text = '<html><title>User - Profile | Pinterest</title></html>'
        res_found = username_tracker.check_site(site, "realuser")
        self.assertEqual(res_found['status'], 'FOUND')

    @patch('requests.get')
    def test_redirect_to_error_url(self, mock_get):
        """Should mark as NOT_FOUND if response redirected to generic landing or login page."""
        import username_tracker
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = 'https://www.pinterest.com/'
        mock_response.text = '<html>Home page</html>'
        mock_get.return_value = mock_response

        site = {
            "name": "Pinterest",
            "url": "https://www.pinterest.com/{}/",
            "error_url": "https://www.pinterest.com/"
        }
        res = username_tracker.check_site(site, "fakeuser")
        self.assertEqual(res['status'], 'NOT_FOUND')

    @patch('requests.get')
    def test_probe_url_usage(self, mock_get):
        """Should query probe_url when specified, while returning canonical profile URL."""
        import username_tracker
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = 'https://medium.com/feed/@realuser'
        mock_response.text = '<rss><channel><title>Stories</title></channel></rss>'
        mock_get.return_value = mock_response

        site = {
            "name": "Medium",
            "url": "https://medium.com/@{}",
            "probe_url": "https://medium.com/feed/@{}"
        }
        res = username_tracker.check_site(site, "realuser")
        self.assertEqual(res['status'], 'FOUND')
        self.assertEqual(res['url'], 'https://medium.com/@realuser')
        mock_get.assert_called_with(
            'https://medium.com/feed/@realuser',
            headers=mock_get.call_args.kwargs['headers'],
            timeout=mock_get.call_args.kwargs['timeout'],
            allow_redirects=True
        )

if __name__ == '__main__':
    unittest.main()
