#!/bin/bash
# OLX Phone Analyzer - Run Script
# Convenience wrapper: uv run syncs .venv from uv.lock, then runs main.py

set -e  # Exit on error

cd "$(dirname "$0")"

# Ensure tqdm progress bars display correctly
export PYTHONUNBUFFERED=1


# Run main.py (which handles setup + logging + async pipeline)
exec uv run main.py "$@"
