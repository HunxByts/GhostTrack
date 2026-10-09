# GhostTrack — maintained local refresh

GhostTrack is a publicly available command-line OSINT utility for **approximate public IP geolocation**, **phone-number plan metadata**, and **public username profile links**. This local refresh is based on [HunxByts/GhostTrack](https://github.com/HunxByts/GhostTrack); it is not an official upstream release. The original project does not publish a license.

## New: Web application with isolated administration

The modernized fork also supports two **separate FastAPI web interfaces**:

- **Private admin** on `http://127.0.0.1:8001` — password-protected dashboard with the public-access switch, aggregate usage and private lookups.
- **Public lookup site** on `http://127.0.0.1:8000` — responsive IP, phone and username tools. Lookups are **disabled by default** until enabled in admin.

To initialize your administrator credentials and start both web services on
your Docker-enabled machine:

```sh
python3 scripts/setup_secrets.py
docker compose build
docker compose up -d ghosttrack-admin ghosttrack-public
```

Both ports bind only to localhost by default. Do not expose the admin port to
the internet. See **[WEB-DEPLOYMENT.md](WEB-DEPLOYMENT.md)** before exposing
the public site, including HTTPS, firewall, reverse proxy and rate limits.

The original CLI remains available with
`docker compose --profile cli run --rm ghosttrack`.

![GhostTrack banner](asset/bn.png)

## What's improved (October 2026)

- Keeps the original four interactive choices: **IP Tracker**, **Show Your IP**, **Phone Number Tracker**, and **Username Tracker**.
- Secure HTTPS calls, explicit timeouts and graceful network/API error handling.
- Accurate IPv4/IPv6 input checks; only public IPs can be geolocated, and map coordinates retain precision.
- Phone parsing supports **any region** with ISO country code (default `ID` for compatibility) and uses updated numbering-plan data.
- Removes broken or retired profile routes such as **Ello**, **StumbleUpon**, and **Periscope**. The old Twitter route is now **X**.
- Explicit `found` / `not_found` results for GitHub and GitLab using their public user APIs; other platforms are **unverified links**, avoiding false positives from login pages and HTTP 200 placeholders.
- Scriptable CLI and `--json` output, without breaking `python3 GhostTR.py`.
- Non-root Docker setup, no exposed ports, and unit tests.

**Privacy and accuracy:** IP geolocation is approximate. Number parsing cannot reveal a phone's live GPS position, actual owner, or current carrier after number porting. An unverified username link does not mean the account exists. Use only public information and respect platform policies.

## Install locally (Python 3.11+)

```sh
# Use this updated local checkout (or your fork containing these commits).
cd /home/ubuntu/greg/Projects/GhostTrack
# Debian/Ubuntu may first require: sudo apt install python3-venv
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python GhostTR.py
```

On Windows, activate with `.venv\\Scripts\\activate`. On Termux, install Python with `pkg install python`; environments that lack `venv` may use their package-specific Python setup.

## Docker

```sh
docker compose build
docker compose run --rm ghosttrack
```

The Docker image is a CLI process (not a web dashboard); it publishes no ports.
For more details, see [DOCKER-SETUP.md](DOCKER-SETUP.md).

## Non-interactive usage

```sh
python GhostTR.py ip 8.8.8.8
python GhostTR.py my-ip
python GhostTR.py phone '+60123456789' --region MY
python GhostTR.py username octocat
python GhostTR.py username octocat --no-check --json
python GhostTR.py ip 1.1.1.1 --json
python GhostTR.py --help
```

With Docker: `docker compose run --rm ghosttrack ip 8.8.8.8 --json`.

Only GitHub and GitLab currently have direct automated verification; all other profiles are browseable links and deliberately marked *unverified* (this is more accurate than treating every HTTP 200 response as a matching account). API access, redirects and rate limits can change over time. Tests mock external services rather than depending on their availability.

## Run tests

```sh
python -m unittest discover -s tests -v
```

## Credits

Original GhostTrack author: [HunxByts](https://github.com/HunxByts).

Original repository: https://github.com/HunxByts/GhostTrack

The original upstream repository does not include a LICENSE file. Confirm permission from the copyright holder before redistributing or publishing modified source code; public source availability alone does not grant a license.
