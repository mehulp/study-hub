#!/usr/bin/env bash
# Dev environment check for the Bookmarks Hub project
# Run this INSIDE your WSL2 Ubuntu terminal, not PowerShell.
# Usage: bash check-dev-env.sh   (or ask Claude Code to run it)

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'

check() {
  local name="$1" cmd="$2" hint="$3"
  if command -v "$cmd" >/dev/null 2>&1; then
    local version
    version=$("$cmd" --version 2>&1 | head -n 1)
    echo -e "${GREEN}✓${NC} $name — $version"
  else
    echo -e "${RED}✗${NC} $name — not found. Install: $hint"
  fi
}

echo "== Core (needed now) =="
check "Docker"      "docker" "Install Docker Desktop on Windows + enable WSL2 integration (Settings > Resources > WSL Integration) — don't apt-install docker inside WSL alongside it"
check "Git"         "git"    "sudo apt update && sudo apt install -y git"
check "VS Code CLI" "code"   "Install the 'WSL' extension in VS Code on Windows, then run 'code .' once from inside this WSL folder"
check "Claude Code" "claude" "npm install -g @anthropic-ai/claude-code  (needs Node.js first, see below)"

echo ""
echo "== Docker Compose (bundled with Docker Desktop) =="
if docker compose version >/dev/null 2>&1; then
  echo -e "${GREEN}✓${NC} Docker Compose — $(docker compose version)"
else
  echo -e "${RED}✗${NC} Docker Compose — not found (should come with Docker Desktop + WSL integration)"
fi

echo ""
echo "== Backend runtime (once we confirm Python vs Node) =="
check "Python 3" "python3" "sudo apt update && sudo apt install -y python3 python3-pip python3-venv"
check "pip"      "pip3"    "included with python3-pip above"
check "Node.js"  "node"    "Install nvm (github.com/nvm-sh/nvm), then: nvm install --lts"
check "npm"      "npm"     "comes with Node.js via nvm above"

echo ""
echo "== Optional but recommended =="
check "psql (Postgres client)" "psql" "sudo apt update && sudo apt install -y postgresql-client"
check "GitHub CLI"             "gh"   "sudo apt update && sudo apt install -y gh"

echo ""
echo "== For later — Twitter OAuth step, not needed yet =="
check "ngrok" "ngrok" "see ngrok.com/download for the Linux install command"

echo ""
echo "Anything marked X under 'Core' or the chosen runtime should be installed before we start building."
