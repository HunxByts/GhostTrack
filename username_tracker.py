"""
username_tracker.py
Resilient, highly accurate OSINT username lookup module for GhostTrack.
Incorporates multi-tier detection techniques from Sherlock and WhatsMyName:
- Username regex pre-validation
- Dedicated probe/API/feed endpoints
- Missing-string / soft-404 detection
- Existence-string verification
- Redirect to error/login URL handling
- Per-request timeouts and isolated error catching
"""

import re
from typing import Callable, Dict, List, Optional, Union
import requests

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Platforms with rich OSINT detection rules (Sherlock & WhatsMyName techniques)
DEFAULT_SITES: List[Dict[str, Union[str, List[str], int]]] = [
    {
        "name": "GitHub",
        "url": "https://github.com/{}",
        "probe_url": "https://api.github.com/users/{}",
        "regex": r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$",
        "e_code": 200,
        "m_code": 404,
    },
    {
        "name": "Reddit",
        "url": "https://www.reddit.com/user/{}",
        "probe_url": "https://www.reddit.com/user/{}/about.json",
        "regex": r"^[a-zA-Z0-9_-]{3,20}$",
        "e_code": 200,
        "m_code": 404,
        "m_string": ['"error": 404', "Sorry, nobody on Reddit goes by that name."],
    },
    {
        "name": "Telegram",
        "url": "https://t.me/{}",
        "regex": r"^[a-zA-Z0-9_]{3,32}[^_]$",
        "m_string": ["noindex, nofollow", "<title>Telegram Messenger</title>"],
        "e_string": "tgme_page_title",
        "e_code": 200,
        "m_code": 200,
    },
    {
        "name": "Pinterest",
        "url": "https://www.pinterest.com/{}/",
        "probe_url": "https://www.pinterest.com/oembed.json?url=https://www.pinterest.com/{}/",
        "e_code": 200,
        "m_code": 400,
        "error_url": "https://www.pinterest.com/",
    },
    {
        "name": "Medium",
        "url": "https://medium.com/@{}",
        "probe_url": "https://medium.com/feed/@{}",
        "e_code": 200,
        "m_code": 404,
    },
    {
        "name": "YouTube",
        "url": "https://www.youtube.com/@{}",
        "m_code": 404,
        "m_string": ["<title>404 Not Found</title>", "This page isn't available"],
    },
    {
        "name": "Twitch",
        "url": "https://www.twitch.tv/{}",
        "probe_url": "https://twitchtracker.com/{}",
        "regex": r"^[a-zA-Z0-9_]{4,25}$",
        "e_string": "Overview</a>",
        "m_string": ["<title>404 Page Not Found", "Page Not Found"],
        "m_code": 404,
    },
    {
        "name": "Twitter / X",
        "url": "https://x.com/{}",
        "regex": r"^[a-zA-Z0-9_]{1,15}$",
        "m_string": ["This account doesn’t exist", "User not found"],
    },
    {
        "name": "SoundCloud",
        "url": "https://soundcloud.com/{}",
        "e_string": '"hydratable":"user"',
        "m_string": [
            "<title>SoundCloud - Hear the world’s sounds</title>",
            "We can’t find that user.",
        ],
        "m_code": 404,
    },
    {
        "name": "Snapchat",
        "url": "https://www.snapchat.com/add/{}",
        "regex": r"^[a-z0-9][a-z0-9._-]{1,15}$",
        "e_string": "is on Snapchat!",
        "m_string": ["NOT_FOUND", "Sorry, couldn't find"],
    },
    {
        "name": "Dribbble",
        "url": "https://dribbble.com/{}",
        "regex": r"^[a-zA-Z0-9_-]+$",
        "m_string": ["Whoops, that page is gone.", "(404)</title>"],
        "m_code": 404,
    },
    {
        "name": "Behance",
        "url": "https://www.behance.net/{}",
        "m_string": ['"entityOwners":[]', "Oops! We can’t find that page"],
        "e_string": '"entityOwners":[{"',
        "m_code": 404,
    },
    {
        "name": "Flickr",
        "url": "https://www.flickr.com/photos/{}/",
        "e_string": "| Flickr",
        "m_string": ["Page not found", "Not Found"],
        "m_code": 404,
    },
    {
        "name": "TikTok",
        "url": "https://www.tiktok.com/@{}",
        "regex": r"^[a-zA-Z0-9._]{2,24}$",
        "m_string": [
            '"statusCode":10221',
            "Couldn't find this account",
            "user-not-found",
        ],
    },
    {
        "name": "Instagram",
        "url": "https://www.instagram.com/{}/",
        "regex": r"^[a-zA-Z0-9._]{1,30}$",
        "e_string": "Posts - See Instagram photos and videos from",
        "m_string": ["Sorry, this page isn't available.", '"routePath":null'],
    },
    {
        "name": "Facebook",
        "url": "https://www.facebook.com/{}/",
        "regex": r"^[a-zA-Z0-9.]{5,}$",
        "e_string": "__isProfile",
        "m_string": [
            "<title>Facebook</title>",
            "This content isn't available right now",
        ],
    },
    {
        "name": "Tumblr",
        "url": "https://www.tumblr.com/{}",
        "regex": r"^[a-zA-Z0-9-]+$",
        "m_string": ['"status":404', "There's nothing here."],
        "m_code": 404,
    },
    {
        "name": "LinkedIn",
        "url": "https://www.linkedin.com/in/{}/",
        "regex": r"^[a-zA-Z0-9-]{3,100}$",
        "m_string": [
            "An exact match for this profile could not be found",
            "Page not found",
        ],
        "m_code": 404,
    },
    {
        "name": "Quora",
        "url": "https://www.quora.com/profile/{}",
        "m_string": ["Page Not Found", "This page may have been moved"],
        "e_string": "Credentials",
        "m_code": 404,
    },
    {
        "name": "Product Hunt",
        "url": "https://www.producthunt.com/@{}",
        "m_string": ["Looks like you're lost", "Page Not Found"],
        "m_code": 404,
    },
]


def check_site(
    site: Dict[str, Union[str, List[str], int]],
    username: str,
    timeout: float = 5.0,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Union[str, int, None]]:
    """Check if a username exists on a specific platform using OSINT verification.

    Implements:
    - Username format regex check (pre-flight validation)
    - Specialized probe URLs (APIs/oembed/feeds) for reliable responses
    - Soft-404 / Missing string inspection (m_string / error_msg)
    - Existence string verification (e_string)
    - Error URL / redirect detection
    - Non-fatal error handling (timeouts, connection drops, rate-limiting)
    """
    url = site["url"].format(username)
    probe_template = site.get("probe_url") or site["url"]
    probe_url = probe_template.format(username)
    site_name = str(site["name"])

    # 1. Regex validation check
    regex_pattern = site.get("regex")
    if regex_pattern and not re.match(str(regex_pattern), username):
        return {
            "name": site_name,
            "status": "NOT_FOUND",
            "url": url,
            "message": "Invalid username format for platform",
            "status_code": None,
        }

    req_headers = {"User-Agent": DEFAULT_USER_AGENT}
    site_headers = site.get("headers")
    if site_headers and isinstance(site_headers, dict):
        req_headers.update(site_headers)
    if headers:
        req_headers.update(headers)

    try:
        response = requests.get(
            probe_url, headers=req_headers, timeout=timeout, allow_redirects=True
        )
        code = response.status_code
        resp_text = response.text or ""
        final_url = response.url or ""

        # 2. Redirect to generic landing or error URL check
        error_url = site.get("error_url")
        if error_url and (final_url == error_url or final_url.startswith(str(error_url))):
            return {
                "name": site_name,
                "status": "NOT_FOUND",
                "url": url,
                "message": "Redirected to landing/error page",
                "status_code": code,
            }

        # 3. HTTP status code check
        m_code = site.get("m_code", 404)
        if code == m_code:
            return {
                "name": site_name,
                "status": "NOT_FOUND",
                "url": url,
                "message": "Username not found",
                "status_code": code,
            }

        if code in (401, 403, 429):
            return {
                "name": site_name,
                "status": "BLOCKED",
                "url": url,
                "message": f"Access restricted / rate-limited (HTTP {code})",
                "status_code": code,
            }

        if code >= 500:
            return {
                "name": site_name,
                "status": "ERROR",
                "url": url,
                "message": f"Server error HTTP {code}",
                "status_code": code,
            }

        # 4. Missing string (m_string / error_msg) check:
        # If response body contains any of these strings, user does not exist even if HTTP 200
        m_strings = site.get("m_string") or site.get("error_msg")
        if m_strings:
            if isinstance(m_strings, str):
                m_strings = [m_strings]
            for err in m_strings:
                if err in resp_text:
                    return {
                        "name": site_name,
                        "status": "NOT_FOUND",
                        "url": url,
                        "message": "Username not found (soft 404 marker)",
                        "status_code": code,
                    }

        # 5. Existence string (e_string) check:
        # If defined, must be present in response body to confirm existence
        e_string = site.get("e_string")
        if e_string:
            if str(e_string) not in resp_text:
                return {
                    "name": site_name,
                    "status": "NOT_FOUND",
                    "url": url,
                    "message": "Profile verification marker missing",
                    "status_code": code,
                }

        # 6. Success check
        e_code = site.get("e_code", 200)
        if code == e_code:
            return {
                "name": site_name,
                "status": "FOUND",
                "url": url,
                "message": "Found",
                "status_code": code,
            }
        else:
            return {
                "name": site_name,
                "status": "ERROR",
                "url": url,
                "message": f"Unexpected response HTTP {code}",
                "status_code": code,
            }

    except requests.exceptions.Timeout:
        return {
            "name": site_name,
            "status": "TIMEOUT",
            "url": url,
            "message": f"Connection timed out (>{timeout}s)",
            "status_code": None,
        }
    except requests.exceptions.ConnectionError:
        return {
            "name": site_name,
            "status": "ERROR",
            "url": url,
            "message": "Connection error / Unreachable",
            "status_code": None,
        }
    except requests.exceptions.RequestException as e:
        return {
            "name": site_name,
            "status": "ERROR",
            "url": url,
            "message": f"Request failed: {type(e).__name__}",
            "status_code": None,
        }
    except Exception as e:
        return {
            "name": site_name,
            "status": "ERROR",
            "url": url,
            "message": f"Unexpected error: {str(e)}",
            "status_code": None,
        }


def search_username(
    username: str,
    sites: Optional[List[Dict[str, Union[str, List[str], int]]]] = None,
    timeout: float = 5.0,
    callback: Optional[Callable[[Dict[str, Union[str, int, None]]], None]] = None,
) -> List[Dict[str, Union[str, int, None]]]:
    """Search for a username across multiple platforms.

    Guarantees every site is processed and no exception can terminate the batch.
    """
    target_sites = sites if sites is not None else DEFAULT_SITES
    results = []

    for site in target_sites:
        res = check_site(site, username, timeout=timeout)
        results.append(res)
        if callback:
            try:
                callback(res)
            except Exception:
                pass

    return results
