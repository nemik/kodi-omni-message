#!/usr/bin/env bash
# Build the zip and serve it over HTTP so Kodi can install it from a URL.
#
#   bash scripts/serve.sh [port]
#
# Use this for a real end-user install test, or when SSH isn't available.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PORT="${1:-8000}"

bash scripts/package.sh

IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo 127.0.0.1)"
cat <<EOF

Serving dist/ at http://$IP:$PORT/

On the Kodi box:
  1. Settings > System > Add-ons > enable "Unknown sources" (once).
  2. Settings > File manager > Add source > http://$IP:$PORT/ > name it "omni".
  3. Settings > Add-ons > Install from zip file > omni > pick the .zip.

Ctrl-C to stop.
EOF

exec uv run --no-project python -m http.server "$PORT" --directory dist
