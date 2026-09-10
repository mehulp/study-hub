#!/usr/bin/env bash
# Starts everything needed for a normal dev session in one command: the
# backend stack (Docker Compose) and the web UI's Vite dev server, which is
# deliberately separate from Compose (Decision #49) and so doesn't come back
# on its own when the backend stack restarts — the exact gap that caused a
# real "unable to reach that url" confusion mid-session once already.
#
# bookmarks-hub and mp-project-study-hub (a separate sibling project, cloned
# from this one) deliberately share the same ports rather than each getting
# their own — simpler, and easier to shut down, at the cost of only ever
# running one of the two at a time. This script refuses to start if the
# *other* one's containers are already up, rather than failing with a
# cryptic Docker port-bind error.
# Usage: bash start-dev.sh

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VITE_LOG="/tmp/$(basename "$REPO_ROOT")-vite-dev.log"

OWN_PROJECT="$(basename "$REPO_ROOT")"
case "$OWN_PROJECT" in
  bookmarks-hub)        SIBLING_PROJECT="mp-project-study-hub" ;;
  mp-project-study-hub) SIBLING_PROJECT="bookmarks-hub" ;;
  *)                    SIBLING_PROJECT="" ;;
esac

if [ -n "$SIBLING_PROJECT" ]; then
  SIBLING_RUNNING="$(docker ps --filter "name=^${SIBLING_PROJECT}-" --format '{{.Names}}' 2>/dev/null)"
  if [ -n "$SIBLING_RUNNING" ]; then
    echo -e "${RED}✗${NC} $SIBLING_PROJECT's stack is already running, and $OWN_PROJECT uses the same ports on purpose (only one runs at a time)."
    echo "  Stop it first:  (cd ../$SIBLING_PROJECT && docker compose down)"
    exit 1
  fi
fi

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
