# GhostTrack Docker setup

See [WEB-DEPLOYMENT.md](WEB-DEPLOYMENT.md) for the web deployment with two
separate FastAPI applications: localhost-only private admin and a public
lookup service disabled by default.

## CLI (unchanged)

```sh
docker compose --profile cli build ghosttrack
docker compose --profile cli run --rm ghosttrack
docker compose --profile cli run --rm ghosttrack ip 8.8.8.8 --json
```

The original CLI remains an independent container and has no published ports.

## Web

```sh
python3 scripts/setup_secrets.py
docker compose build
docker compose up -d ghosttrack-admin ghosttrack-public
```

- Admin: `http://127.0.0.1:8001` (never publicly expose)
- Public: `http://127.0.0.1:8000` (initially disabled)

## Environment limitations

The Linux VM coding connector can run inside a restricted container without
a Docker executable or access to the host daemon. If so, build/run on the
Docker-enabled Ubuntu host. Do not mount the Docker socket into untrusted
services solely to run the app.
