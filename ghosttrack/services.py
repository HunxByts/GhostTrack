"""Small, testable services for public OSINT lookups."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import quote

import phonenumbers
import requests
from phonenumbers import carrier, geocoder, timezone

from .platforms import PROFILES

DEFAULT_TIMEOUT = 8
HEADERS = {"User-Agent": "GhostTrack/3.0 (public OSINT; no scraping)"}


class LookupError(Exception):
    """A recoverable validation, network or lookup failure."""


def get_json(url: str, *, timeout: float = DEFAULT_TIMEOUT):
    """Fetch JSON over TLS with a bounded timeout and useful errors."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.Timeout as exc:
        raise LookupError("Request timed out. Try again later.") from exc
    except (requests.RequestException, ValueError) as exc:
        raise LookupError(f"Could not retrieve data: {exc}") from exc


def ip_lookup(address: str, *, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """Return approximate geolocation for a public IPv4/IPv6 address."""
    try:
        ip = ipaddress.ip_address(address.strip())
    except ValueError as exc:
        raise LookupError("Enter a valid IPv4 or IPv6 address.") from exc
    if not ip.is_global:
        raise LookupError("This address is not globally routable; no public geolocation is available.")

    data = get_json(f"https://ipwho.is/{quote(str(ip), safe=':')}", timeout=timeout)
    if not isinstance(data, dict) or data.get("success") is False:
        message = data.get("message", "Unexpected API response") if isinstance(data, dict) else "Unexpected API response"
        raise LookupError(f"IP lookup failed: {message}")

    connection = data.get("connection") or {}
    tz = data.get("timezone") or {}
    flag = data.get("flag") or {}
    if not all(isinstance(x, dict) for x in (connection, tz, flag)):
        raise LookupError("IP service returned an unexpected data format.")

    latitude, longitude = data.get("latitude"), data.get("longitude")
    maps = None
    if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            maps = f"https://www.google.com/maps/search/?api=1&query={latitude}%2C{longitude}"

    return {
        "ip": str(ip),
        "type": data.get("type"),
        "country": data.get("country"),
        "country_code": data.get("country_code"),
        "city": data.get("city"),
        "region": data.get("region"),
        "region_code": data.get("region_code"),
        "continent": data.get("continent"),
        "continent_code": data.get("continent_code"),
        "latitude": latitude,
        "longitude": longitude,
        "map_url": maps,
        "is_eu": data.get("is_eu"),
        "postal": data.get("postal"),
        "calling_code": data.get("calling_code"),
        "capital": data.get("capital"),
        "borders": data.get("borders"),
        "flag": flag.get("emoji"),
        "connection": {
            key: connection.get(key) for key in ("asn", "org", "isp", "domain")
        },
        "timezone": {
            key: tz.get(key) for key in
            ("id", "abbr", "is_dst", "offset", "utc", "current_time")
        },
        "note": "IP geolocation is approximate and does not identify a person's precise location.",
    }


def my_ip(*, timeout: float = DEFAULT_TIMEOUT) -> dict:
    data = get_json("https://api.ipify.org?format=json", timeout=timeout)
    value = data.get("ip") if isinstance(data, dict) else None
    try:
        address = ipaddress.ip_address(value)
    except (TypeError, ValueError) as exc:
        raise LookupError("IP service returned an invalid address.") from exc
    return {"ip": str(address), "note": "This is the public egress IP seen by the lookup service."}


def phone_lookup(number: str, *, region: str = "ID") -> dict:
    """Return numbering-plan metadata; no network or live tracking is performed."""
    region = region.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", region):
        raise LookupError("Region must be a two-letter country code, such as MY, ID, or US.")
    try:
        parsed = phonenumbers.parse(number.strip(), region)
    except phonenumbers.NumberParseException as exc:
        raise LookupError(f"Could not parse phone number: {exc}") from exc

    number_type = phonenumbers.number_type(parsed)
    type_names = {
        phonenumbers.PhoneNumberType.MOBILE: "mobile",
        phonenumbers.PhoneNumberType.FIXED_LINE: "fixed line",
        phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed line or mobile",
        phonenumbers.PhoneNumberType.VOIP: "VoIP",
        phonenumbers.PhoneNumberType.TOLL_FREE: "toll free",
        phonenumbers.PhoneNumberType.PREMIUM_RATE: "premium rate",
    }
    return {
        "region": phonenumbers.region_code_for_number(parsed),
        "country_code": parsed.country_code,
        "national_number": str(parsed.national_number),
        "e164": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
        "international": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
        "national": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
        "mobile_dialing": phonenumbers.format_number_for_mobile_dialing(
            parsed, region, with_formatting=True
        ),
        "valid": phonenumbers.is_valid_number(parsed),
        "possible": phonenumbers.is_possible_number(parsed),
        "type": type_names.get(number_type, "other / unknown"),
        "area_description": geocoder.description_for_number(parsed, "en"),
        "original_carrier": carrier.name_for_number(parsed, "en"),
        "timezones": list(timezone.time_zones_for_number(parsed)),
        "note": (
            "Numbering-plan metadata only; this cannot determine a person's "
            "live location, current carrier after porting, or ownership."
        ),
    }


def _github_status(username: str, *, timeout: float) -> tuple[str, str]:
    try:
        data = get_json(
            f"https://api.github.com/users/{quote(username, safe='')}", timeout=timeout
        )
    except LookupError as exc:
        # Only a genuine 404 is conclusive: rate limits, WAF blocks and timeouts are not.
        if isinstance(exc.__cause__, requests.HTTPError) and exc.__cause__.response is not None:
            if exc.__cause__.response.status_code == 404:
                return "not_found", "GitHub API: user not found"
        return "unverified", "GitHub API unavailable / rate limited"
    login = data.get("login") if isinstance(data, dict) else None
    if isinstance(login, str) and login.casefold() == username.casefold():
        return "found", "Verified through GitHub's public user API"
    return "unverified", "Unexpected GitHub API response"


def _gitlab_status(username: str, *, timeout: float) -> tuple[str, str]:
    try:
        data = get_json(
            f"https://gitlab.com/api/v4/users?username={quote(username, safe='')}",
            timeout=timeout,
        )
    except LookupError:
        return "unverified", "GitLab API unavailable / rate limited"
    if not isinstance(data, list):
        return "unverified", "Unexpected GitLab API response"
    if any(
        isinstance(item, dict)
        and str(item.get("username", "")).casefold() == username.casefold()
        for item in data
    ):
        return "found", "Verified through GitLab's public user API"
    return "not_found", "GitLab public user API returned no matching profile"


def username_lookup(username: str, *, check: bool = True, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """Produce current profile links; verify only platforms with reliable public APIs."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,39}", username) or username in {".", ".."}:
        raise LookupError("Username must be 1-39 characters: letters, digits, _, ., or -.")

    profiles = []
    for platform, template in PROFILES:
        status, explanation = "unverified", "Profile link only; existence not verified"
        if check and platform == "GitHub":
            status, explanation = _github_status(username, timeout=timeout)
        elif check and platform == "GitLab":
            status, explanation = _gitlab_status(username, timeout=timeout)
        profiles.append({
            "platform": platform,
            "url": template.format(username=quote(username, safe='')),
            "status": status,
            "detail": explanation,
        })
    return {
        "username": username,
        "profiles": profiles,
        "note": (
            "Found means verified via a public API. Unverified links may not exist; "
            "a page returning HTTP 200 or a login screen is not proof of an account."
        ),
    }
