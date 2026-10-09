#!/usr/bin/env python3
"""Generate GhostTrack administrator credentials locally without dependencies.

Usage: python3 scripts/setup_secrets.py [--directory .secrets]
The password is prompted securely (not echoed or stored in shell history).
"""
import argparse
import getpass
import os
import secrets
import sys
from pathlib import Path

# When invoked by python scripts/setup_secrets.py, ensure package is importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ghosttrack.web.auth import hash_password


def main():
    parser = argparse.ArgumentParser(description="Create local GhostTrack admin secrets")
    parser.add_argument("--directory", default=".secrets", help="Destination for secret files")
    args = parser.parse_args()
    root = Path(args.directory)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if any((root / f).exists() for f in ("admin_password_hash", "session_secret")):
        parser.error("Secrets already exist. Move them to a secure backup before reinitializing.")
    password = getpass.getpass("New administrator password (16+ characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        parser.error("Passwords do not match")
    try:
        hashed = hash_password(password)
    except ValueError as exc:
        parser.error(str(exc))
    for filename, content in (
        ("admin_password_hash", hashed),
        ("session_secret", secrets.token_urlsafe(48)),
    ):
        path = root / filename
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(content + "\n")
    # Prepare a writable bind mount for the unprivileged web containers.
    data = Path(".data")
    data.mkdir(mode=0o700, exist_ok=True)
    print(f"Admin credentials saved in {root}/ (keep secret; never commit).")


if __name__ == "__main__":
    main()
