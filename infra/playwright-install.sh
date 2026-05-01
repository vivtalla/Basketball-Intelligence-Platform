#!/bin/bash
# CourtVue Labs — install Playwright Chromium binary for the PST scraper.
# Run once after pip install of requirements.txt on the VM.
# Usage: bash infra/playwright-install.sh
set -euo pipefail

PYTHON="/home/ubuntu/bip/backend/venv/bin/python"
PLAYWRIGHT="/home/ubuntu/bip/backend/venv/bin/playwright"

echo "[playwright-install] Installing Playwright package..."
/home/ubuntu/bip/backend/venv/bin/pip install -q "playwright>=1.40.0"

echo "[playwright-install] Installing Chromium browser + system dependencies..."
"$PLAYWRIGHT" install chromium --with-deps

echo "[playwright-install] Verifying install..."
"$PYTHON" -c "from playwright.sync_api import sync_playwright; print('[playwright-install] OK')"

echo "[playwright-install] Done. Chromium binary at ~/.cache/ms-playwright/"
