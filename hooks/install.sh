#!/usr/bin/env bash
# Install this repo's git hooks into .git/hooks. Run once after cloning.
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
HERE="$(cd "$(dirname "$0")" && pwd)"
for h in pre-commit; do
  cp "$HERE/$h" "$ROOT/.git/hooks/$h"
  chmod +x "$ROOT/.git/hooks/$h"
  echo "installed $h"
done
