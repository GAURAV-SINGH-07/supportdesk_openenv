#!/usr/bin/env bash
set -euo pipefail

PING_URL="${1:-}"
REPO_DIR="${2:-.}"

if [ -z "$PING_URL" ]; then
  echo "Usage: $0 <hf_space_url> [repo_dir]"
  exit 1
fi

echo "[1/4] Building Docker image..."
docker build -t supportdesk-openenv "$REPO_DIR"

echo "[2/4] Checking required files..."
test -f "$REPO_DIR/openenv.yaml"
test -f "$REPO_DIR/inference.py"
test -f "$REPO_DIR/Dockerfile"
test -f "$REPO_DIR/server.py"
echo "Required files found."

echo "[3/4] Optional OpenEnv validation..."
if command -v openenv >/dev/null 2>&1; then
  (cd "$REPO_DIR" && openenv validate) || true
else
  echo "openenv CLI not installed; skipping openenv validate."
fi

echo "[4/4] Pinging Space reset endpoint..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
  -H "Content-Type: application/json" \
  -d '{}' \
  "${PING_URL%/}/reset")

if [ "$HTTP_CODE" != "200" ]; then
  echo "Space /reset returned HTTP $HTTP_CODE"
  exit 1
fi

echo "Validation passed."
