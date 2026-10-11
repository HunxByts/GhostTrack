import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import requests

class TestIntegration(unittest.TestCase):
    @patch('builtins.input', return_value='testuser')
    @patch('requests.get')
    def test_tracklu_survives_timeout_and_errors(self, mock_get, mock_input):
        import GhostTR

        # Simulate: one site raises Timeout, another raises ConnectionError, another returns 200
        call_count = 0
        def side_effect(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise requests.exceptions.Timeout("Test timeout")
            elif call_count == 2:
                raise requests.exceptions.ConnectionError("Test connection error")
            else:
                resp = MagicMock()
                resp.status_code = 200
                return resp

        mock_get.side_effect = side_effect

        captured_stdout = io.StringIO()
        with patch('sys.stdout', captured_stdout):
            # Calling TrackLu should NOT raise or cancel early
            GhostTR.TrackLu()

        output = captured_stdout.getvalue()
        import re
        clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
        # Must display the information header
        self.assertIn("SHOW INFORMATION USERNAME", clean_output)
        # Must show results that succeeded as well
        self.assertIn("[ + ]", clean_output)
        # Must show flagged error or timed out sites
        self.assertTrue("[ ! ]" in clean_output or "timed out" in clean_output.lower() or "error" in clean_output.lower())
        # Must show summary line
        self.assertIn("Summary:", clean_output)
        self.assertIn("Flagged/Unresponsive", clean_output)

if __name__ == '__main__':
    unittest.main()
