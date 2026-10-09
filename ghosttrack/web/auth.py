"""Hardened short-lived admin session and password verification."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from pathlib import Path

SESSION_AGE = 4 * 3600


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    if len(password) < 16:
        raise ValueError("Admin password must have at least 16 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$16384$8$1$" + _b64(salt) + "$" + _b64(digest)


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, n, r, p, salt, hashed = stored_hash.split("$")
        if (algorithm, n, r, p) != ("scrypt", "16384", "8", "1"):
            return False
        expected, salt_bytes = _decode(hashed), _decode(salt)
        if len(expected) != 32 or len(salt_bytes) != 16:
            return False
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt_bytes,
                                n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


class AdminAuth:
    def __init__(self, secret_dir: str):
        from itsdangerous import URLSafeTimedSerializer

        folder = Path(secret_dir)
        password_hash = (folder / "admin_password_hash").read_text(encoding="utf-8").strip()
        session_secret = (folder / "session_secret").read_text(encoding="utf-8").strip()
        if not password_hash.startswith("scrypt$16384$8$1$"):
            raise ValueError("Admin password hash is missing or invalid.")
        if len(session_secret) < 40:
            raise ValueError("Session secret must be at least 40 characters.")
        self.password_hash = password_hash
        self.signer = URLSafeTimedSerializer(session_secret, salt="ghosttrack-admin-v1",
                                              signer_kwargs={"digest_method": hashlib.sha256})

    def authenticate(self, password: str) -> bool:
        # Keep the stored password hash out of logs and responses.
        return verify_password(password, self.password_hash)

    def new_session(self) -> tuple[str, str]:
        csrf = secrets.token_urlsafe(32)
        return self.signer.dumps({"role": "admin", "csrf": csrf}), csrf

    def parse_session(self, value: str | None) -> str | None:
        if not value:
            return None
        from itsdangerous import BadSignature, SignatureExpired

        try:
            payload = self.signer.loads(value, max_age=SESSION_AGE)
        except (BadSignature, SignatureExpired, ValueError, TypeError):
            return None
        if isinstance(payload, dict) and payload.get("role") == "admin":
            csrf = payload.get("csrf")
            if isinstance(csrf, str) and len(csrf) > 20:
                return csrf
        return None
