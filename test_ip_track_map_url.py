"""
Regression test: IP_Track map URL must preserve float-precision coordinates.

The bug in GhostTR.py lines 59–60:
    lat = int(ip_data['latitude'])
    lon = int(ip_data['longitude'])

int() truncates toward zero, discarding the fractional part of the coordinate.
For a city like San Francisco (37.7749, -122.4194) the generated Google Maps
URL becomes https://www.google.com/maps/@37,-122,8z — placing the pin roughly
43 km from the actual IP location.

This test patches the API call so no network access is required and verifies
the URL contains the original float values.
"""

import re
import sys
import unittest
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CASES = [
    # (latitude, longitude, description)
    (37.7749,  -122.4194, "San Francisco, CA"),
    (-33.8688,  151.2093, "Sydney, Australia"),
    (51.5074,   -0.1278,  "London, UK"),
    (48.8566,    2.3522,  "Paris, France"),
    (-1.2921,   36.8219,  "Nairobi, Kenya"),
    (0.3476,    32.5825,  "Kampala, Uganda"),
    (-0.0236,  109.3425,  "Pontianak, Indonesia"),
]


def _make_ip_response(lat, lon):
    """Return a mock requests.Response-like object for the given coordinates."""
    import json as _json
    data = {
        "type": "IPv4",
        "country": "Testland",
        "country_code": "TL",
        "city": "Testville",
        "continent": "Testinent",
        "continent_code": "TI",
        "region": "Test Region",
        "region_code": "TR",
        "latitude": lat,
        "longitude": lon,
        "is_eu": False,
        "postal": "00000",
        "calling_code": "+0",
        "capital": "Testcap",
        "borders": "",
        "flag": {"emoji": "🏳"},
        "connection": {"asn": 0, "org": "TestOrg", "isp": "TestISP", "domain": "test.invalid"},
        "timezone": {
            "id": "Test/Zone",
            "abbr": "TZ",
            "is_dst": False,
            "offset": 0,
            "utc": "+00:00",
            "current_time": "00:00:00",
        },
    }
    mock_resp = MagicMock()
    mock_resp.text = _json.dumps(data)
    return mock_resp


def _capture_map_url(lat, lon):
    """
    Call the IP_Track logic with a stubbed API response and capture the
    printed map URL without starting the interactive loop or clearing the
    terminal.
    """
    import io
    import builtins

    printed_lines = []
    original_print = builtins.print

    def capturing_print(*args, **kwargs):
        line = " ".join(str(a) for a in args)
        printed_lines.append(line)

    mock_resp = _make_ip_response(lat, lon)

    with patch("builtins.input", return_value="1.2.3.4"), \
         patch("builtins.print", side_effect=capturing_print), \
         patch("requests.get", return_value=mock_resp), \
         patch("time.sleep"), \
         patch("os.system"):

        # Import here so patches take effect before module-level code runs
        import importlib
        import GhostTR  # noqa: F401 – side-effect import for module-level code
        importlib.reload(GhostTR)   # reload to pick up patches

        # Execute the unwrapped IP_Track function body by calling the option
        # via its wrapper (the @is_option decorator calls run_banner then IP_Track).
        try:
            GhostTR.IP_Track()
        except Exception:
            pass  # interactive prompts / mock side-effects are expected

    return printed_lines


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lat,lon,desc", CASES)
def test_ip_track_map_url_preserves_float_coordinates(lat, lon, desc):
    """
    The Maps URL printed by IP_Track must contain the original float latitude
    and longitude, not integers truncated toward zero.

    Fails on the baseline (int() cast); passes after the fix (float() or
    direct use of the API value without casting).
    """
    printed = _capture_map_url(lat, lon)
    map_lines = [l for l in printed if "maps.google" in l or "google.com/maps" in l]
    assert map_lines, f"[{desc}] No Google Maps URL was printed; lines: {printed}"

    url = map_lines[0]
    # Exact float strings must appear in the URL
    assert str(lat) in url and str(lon) in url, (
        f"[{desc}] Expected float coords ({lat},{lon}) in URL, got: {url!r}\n"
        "Likely cause: int() cast in GhostTR.py truncates the fractional part."
    )
