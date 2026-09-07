#!/usr/bin/env bash
# Starts everything needed for a normal dev session in one command: the
# backend stack (Docker Compose) and the web UI's Vite dev server, which is
# deliberately separate from Compose (Decision #49) and so doesn't come back
# on its own when the backend stack restarts — the exact gap that caused a
# real "unable to reach that url" confusion mid-session once already.
# Usage: bash start-dev.sh

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VITE_LOG="/tmp/bookmarks-hub-vite-dev.log"

echo "== Backend stack (Docker Compose) =="
(cd "$REPO_ROOT" && docker compose up -d)

echo ""
echo "== Web UI (Vite dev server) =="
if curl -sS -o /dev/null -w '' http://localhost:5173/ 2>/dev/null; then
  echo -e "${GREEN}✓${NC} already running at http://localhost:5173"
else
  (cd "$REPO_ROOT/web" && nohup npm run dev -- --port 5173 > "$VITE_LOG" 2>&1 &)
  sleep 2
  if curl -sS -o /dev/null -w '' http://localhost:5173/ 2>/dev/null; then
    echo -e "${GREEN}✓${NC} started at http://localhost:5173 (log: $VITE_LOG)"
  else
    echo -e "${YELLOW}!${NC} didn't come up in time — check $VITE_LOG"
  fi
fi

echo ""
echo "Ready: http://localhost:5173"
echo "(ngrok tunnel for Twitter OAuth testing is separate — start it yourself when needed, it isn't part of daily startup)"
