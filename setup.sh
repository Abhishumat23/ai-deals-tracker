#!/usr/bin/env bash
# ============================================================
# AI Deals Tracker — Quick Setup Script (macOS / Linux)
# Run this once from the project root:
#   chmod +x setup.sh && ./setup.sh
# ============================================================

set -e  # Exit on any error

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[setup]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }

# ─── Python version check ───────────────────────────────────
if ! python3 --version | grep -qE "3\.(1[1-9]|[2-9][0-9])"; then
  warn "Python 3.11+ is recommended. You have: $(python3 --version)"
fi

# ─── Backend ────────────────────────────────────────────────
log "Setting up Python backend..."
cd backend

if [ ! -d "venv" ]; then
  python3 -m venv venv
  log "Created virtual environment"
fi

source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
log "Python dependencies installed"

log "Installing Playwright Chromium..."
playwright install chromium
log "Playwright Chromium installed"

# Create data directory
mkdir -p data
log "Data directory ready"

deactivate
cd ..

# ─── Frontend ───────────────────────────────────────────────
log "Setting up Next.js frontend..."
cd frontend
npm install --silent
log "Node dependencies installed"
cd ..

# ─── .env ───────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  cp .env.example .env
  log ".env created from .env.example"
  warn "→ Edit .env and add your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID"
else
  log ".env already exists — skipping"
fi

echo ""
echo "═══════════════════════════════════════════════"
echo "  Setup complete! Next steps:"
echo ""
echo "  1. Edit .env and add your Telegram credentials"
echo ""
echo "  2. Terminal 1 — start backend:"
echo "     cd backend && source venv/bin/activate"
echo "     uvicorn app:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "  3. Terminal 2 — start frontend:"
echo "     cd frontend && npm run dev"
echo ""
echo "  4. Open http://localhost:3000"
echo "═══════════════════════════════════════════════"
