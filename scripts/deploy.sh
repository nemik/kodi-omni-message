#!/usr/bin/env bash
# Push the add-on to the Kodi test PC and restart its service.
#
#   bash scripts/deploy.sh
#
# Config comes from scripts/deploy.env (see deploy.env.example). This is the
# fast iteration path: no zip, no clicking around on the TV.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADDON_ID="service.omnimessage"
cd "$ROOT"

ENV_FILE="${DEPLOY_ENV:-scripts/deploy.env}"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a && source "$ENV_FILE" && set +a
elif [[ -z "${KODI_HOST:-}" ]]; then
  echo "no $ENV_FILE — copy scripts/deploy.env.example to it and fill it in" >&2
  exit 1
fi

: "${KODI_HOST:?set KODI_HOST}"
: "${KODI_SSH_USER:?set KODI_SSH_USER}"
KODI_ADDON_DIR="${KODI_ADDON_DIR:-.kodi/addons}"
KODI_RPC_PORT="${KODI_RPC_PORT:-8080}"

# The path must stay unexpanded until it reaches the remote machine. Sourcing
# deploy.env expands a leading ~ against *this* machine's home, so undo that:
# a relative path is what we want, since both ssh and rsync resolve it against
# the remote user's home directory.
KODI_ADDON_DIR="${KODI_ADDON_DIR#"$HOME"/}"
KODI_ADDON_DIR="${KODI_ADDON_DIR#\~/}"

SSH=(ssh -o ConnectTimeout=10 "$KODI_SSH_USER@$KODI_HOST")

echo "==> checking $KODI_ADDON_DIR on $KODI_HOST"
set +e
"${SSH[@]}" "test -d '$KODI_ADDON_DIR' || exit 3; mkdir -p '$KODI_ADDON_DIR/$ADDON_ID'"
probe=$?
set -e
if [[ $probe -eq 3 ]]; then
  cat >&2 <<EOF
'$KODI_ADDON_DIR' does not exist on $KODI_HOST.
Set KODI_ADDON_DIR in $ENV_FILE to Kodi's add-on directory there, e.g.
  .kodi/addons            Linux desktop / macOS-style home install
  /storage/.kodi/addons   LibreELEC / CoreELEC
Paths without a leading / are taken relative to $KODI_SSH_USER's home.
EOF
  exit 1
elif [[ $probe -ne 0 ]]; then
  echo "ssh to $KODI_SSH_USER@$KODI_HOST failed" >&2
  exit 1
fi

TARGET="$KODI_SSH_USER@$KODI_HOST:$KODI_ADDON_DIR/$ADDON_ID/"
echo "==> syncing to $TARGET"
rsync -az --delete \
  -e "ssh -o ConnectTimeout=10" \
  --exclude '__pycache__' --exclude '*.pyc' --exclude '.DS_Store' \
  "$ADDON_ID/" "$TARGET"

rpc() {
  local enabled="$1" auth=()
  [[ -n "${KODI_RPC_USER:-}" ]] && auth=(-u "$KODI_RPC_USER:${KODI_RPC_PASS:-}")
  # Kodi answers HTTP 200 with an "error" object for an unknown add-on, so the
  # body has to be inspected — curl's exit status alone says nothing.
  curl -sS --max-time 10 "${auth[@]}" \
    -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"Addons.SetAddonEnabled\",\"params\":{\"addonid\":\"$ADDON_ID\",\"enabled\":$enabled}}" \
    "http://$KODI_HOST:$KODI_RPC_PORT/jsonrpc"
}

echo
echo "==> restarting the service over JSON-RPC"
# Disabling then re-enabling stops and restarts the service process, which is
# what makes Kodi pick up the new Python. addon.xml and settings.xml changes
# still need a full Kodi restart.
response="$(rpc false || true)"
if [[ "$response" == *'"error"'* || -z "$response" ]]; then
  echo
  if [[ -n "${KODI_RESTART_CMD:-}" ]]; then
    echo "==> Kodi has not registered the add-on; running KODI_RESTART_CMD"
    "${SSH[@]}" "$KODI_RESTART_CMD"
    echo "Kodi restarted; it will pick the add-on up on startup."
    exit 0
  fi
  cat >&2 <<EOF
Kodi did not accept the restart: $response

The files are in place, but Kodi only scans for new add-ons at startup, so a
brand-new add-on is unknown to it until then. Do one of these once:

  * restart Kodi on $KODI_HOST, or
  * install the zip normally: bash scripts/serve.sh

After that, this script restarts the service on its own. To have it restart
Kodi for you, set KODI_RESTART_CMD in $ENV_FILE, e.g.
  KODI_RESTART_CMD="systemctl --user restart kodi"
EOF
  exit 1
fi
sleep 1
rpc true >/dev/null
echo "service restarted"

echo
echo "tail the log with:"
echo "  ssh $KODI_SSH_USER@$KODI_HOST 'tail -f ~/.kodi/temp/kodi.log' | grep -i omnimessage"
