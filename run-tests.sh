#!/usr/bin/env bash
# Runs every service's test suite in sequence.
# Requires Postgres to be up (docker compose up -d postgres) and each
# service's venv already set up (pip install -r requirements-dev.txt).
# Usage: bash run-tests.sh

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

overall_status=0

# The test database isn't created by any docker-compose-managed step — it's
# only ever existed because of a one-off manual `createdb`, which doesn't
# survive a volume reset (docker compose down -v, or a fresh clone). Ensured
# here instead of relying on a human remembering to recreate it.
if ! docker compose exec -T postgres psql -U study_hub -d study_hub -tc \
    "SELECT 1 FROM pg_database WHERE datname = 'study_hub_test'" 2>/dev/null | grep -q 1; then
  echo "Creating study_hub_test database (didn't exist)..."
  docker compose exec -T postgres createdb -U study_hub study_hub_test
fi

run_suite() {
  local service="$1"
  echo ""
  echo "== $service =="
  if (cd "$REPO_ROOT/services/$service" && ./venv/bin/python -m pytest -q); then
    echo -e "${GREEN}✓${NC} $service passed"
  else
    echo -e "${RED}✗${NC} $service FAILED"
    overall_status=1
  fi
}

run_suite auth
run_suite items
run_suite board
run_suite connectors
run_suite gateway

echo ""
if [ $overall_status -eq 0 ]; then
  echo -e "${GREEN}All suites passed.${NC}"
else
  echo -e "${RED}One or more suites failed — see above.${NC}"
fi

exit $overall_status
