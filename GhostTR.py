#!/usr/bin/env python3
"""Compatibility launcher for GhostTrack's original entry point."""

from ghosttrack.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
