#!/usr/bin/env python3
"""
Environment Sync
================
Keeps .venv in sync with pyproject.toml + uv.lock via `uv sync` (a no-op when
already in sync). Prefer launching with `uv run main.py`, which syncs on its own.
"""

import shutil
import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.parent


def setup_env() -> None:
    """Sync the project environment; raises if uv is missing or the sync fails."""
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv not found on PATH — install: https://docs.astral.sh/uv/")
    subprocess.run([uv, "sync", "--quiet", "--project", str(PROJECT_DIR)], check=True)


if __name__ == "__main__":
    setup_env()
