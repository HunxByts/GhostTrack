# GhostTrack: private admin + separately controlled public web server

Two **separate FastAPI applications** run on the same Docker image, sharing
only an SQLite file in the gitignored `.data/` bind mount:

- **Private admin**, `127.0.0.1:8001`: password-protected login, signed
  four-hour session, CSRF-protected actions, enable/disable public service,
  aggregate metrics, private lookup tools including server egress IP.
- **Public**, `127.0.0.1:8000` by default: responsive web interface for
  public IP, numbering-plan metadata, and username links. **Starts disabled**.
  Public never imports/loads the administrator secret files.

Neither interface automatically listens on the public host network. The
admin host port is always bound to loopback. Do not publicly proxy admin.

## Deployment on the Docker-enabled host

From the updated repository checkout:

```sh
cd /home/ubuntu/greg/Projects/GhostTrack

# Generates .secrets/admin_password_hash and .secrets/session_secret
# without echoing your password or writing it into the shell history.
python3 scripts/setup_secrets.py

docker compose build
docker compose up -d ghosttrack-admin ghosttrack-public
docker compose ps
```

A password at least 16 characters long is required. Save it securely.
The credential files are chmod 0600 and ignored by Git. Do not commit, upload
or share them. The setup script also creates `.data/` for SQLite.
The Docker web image runs as UID/GID 1000 and expects
`.secrets` to be readable by this same UID; run the setup script as the normal
Ubuntu user with UID 1000. On hosts with a different UID, adapt the Docker
image's USER and `/data` permissions (or adjust the secret-file ownership
with appropriate permissions) before running. Do not set the admin container
to root just to work around permissions.

By default, both interfaces are **only accessible on the Docker host**:

- Private admin: `http://127.0.0.1:8001`
- Public preview: `http://127.0.0.1:8000`

For accessing the private admin from your own laptop, use an SSH tunnel:

```sh
ssh -L 8001:127.0.0.1:8001 ubuntu@YOUR_VM
```

Then open `http://localhost:8001`. You can also securely proxy admin through
a properly authenticated Tailscale-only route, but **never route its port on a
public domain**. Session cookies use `SameSite=Strict` and `HttpOnly`.
For a Tailscale HTTPS reverse proxy, set `GHOSTTRACK_SECURE_COOKIE=true`
on the admin service and restart it.

Log in and use **Enable public lookups** when ready. The public server
checks the switch in SQLite on every request; disabled responses are 503.
It remains disabled after first startup until explicitly enabled.

## Public internet exposure (optional)

A public domain should be deployed only behind an HTTPS reverse proxy with
perimeter rate limiting, abuse controls, request-size limits, and monitoring.
Protect against large-scale username enumeration. The built-in rate limit is
in-memory, per process, and keyed by immediate peer IP. Behind a reverse proxy
this will often be **the proxy's IP** (we deliberately ignore client-provided
`X-Forwarded-For` headers). Configure trusted-client-aware limits in the
reverse proxy; keep one Uvicorn worker per application. For remote access,
enable `GHOSTTRACK_PUBLIC_BIND=0.0.0.0` in a local, gitignored `.env`,
apply host firewall rules, and publish **only** the public service through
your trusted proxy.

Do not expose port 8001. The admin bind is always 127.0.0.1.

## CLI continues to work

```sh
docker compose --profile cli run --rm ghosttrack
docker compose --profile cli run --rm ghosttrack ip 8.8.8.8 --json
python3 GhostTR.py --help
```

## Endpoints

Public:

- `GET /`: responsive public web interface
- `GET /api/status`: public enabled indicator
- `POST /api/lookup/ip`, `/phone`, `/username`: JSON
  `{"value":"8.8.8.8","region":"ID","check":true}`
- `GET /healthz`: process liveness

Admin (loopback only):

- `GET /`: admin web interface
- `POST /api/admin/login`: password
- `GET /api/admin/me`: authenticated session + CSRF token
- `POST /api/admin/logout`: authenticated + CSRF token
- `GET /api/admin/summary`: aggregated daily counts
- `POST /api/admin/public-access`: `{"enabled":true}` with CSRF token
- `POST /api/lookup/{ip|phone|username|my-ip}`: authenticated + CSRF token

POST calls require the `X-GhostTrack-UI: 1` header. Authenticated admin writes
also require the `X-CSRF-Token` header returned by the login or /me endpoint.
The browser frontend handles both automatically.

## Security properties and limitations

- Cookie sessions are signed, short-lived, HttpOnly, SameSite Strict.
- Passwords are stored as salted scrypt hashes; no sample default credentials.
- No cross-origin API permissions or outbound network requests from the browser.
- Strong security headers, no external JavaScript/font dependencies.
- Requests validated and rate-limited; external lookups use HTTPS + timeouts.
- Both containers are non-root, read-only-root filesystem, dropped capabilities.
- No raw search terms, target phone numbers, target IP addresses or visitor IPs
  stored; only daily aggregate counts by interface, tool and outcome.
- A leaked session cookie remains usable until it expires; logout deletes only
  the browser cookie. Rotate the session secret to invalidate every session.
- Rate limits are process-local, **not distributed**. Put a trusted reverse proxy
  in front of Internet-facing installs and add network-level DoS protection.
- Location results represent public IP geolocation and telephone numbering
  metadata, not a device's exact or live location.
- This code is a local/fork modernization. Upstream has no published license;
  verify permissions before redistributing further.

## Tests

Install the optional web dependencies and HTTP client:

```sh
python3 -m pip install -r web-requirements.txt 'httpx>=0.27,<1'
python3 -m unittest discover -s tests -v
```

For Docker verification: `docker compose config`, `docker compose build`,
`docker compose up -d`, then inspect `docker compose ps` and health checks.
