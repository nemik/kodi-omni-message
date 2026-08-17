#!/usr/bin/env bash
# Drive the add-on over Kodi's JSON-RPC API, the same way Homebridge does.
#
#   bash scripts/rpc.sh on        block playback and show the message
#   bash scripts/rpc.sh off       allow all playback (PIN from deploy.env)
#   bash scripts/rpc.sh status    read the published state
#
# "off" stays off until something turns it back on: this script, Homebridge, or
# the add-on's own settings screen in Kodi.
#
# Connection details come from scripts/deploy.env; the PIN comes from
# KODI_UNLOCK_PIN there, or the OMNI_PIN environment variable.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${DEPLOY_ENV:-scripts/deploy.env}"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a && source "$ENV_FILE" && set +a
fi
: "${KODI_HOST:?set KODI_HOST in $ENV_FILE}"
KODI_RPC_PORT="${KODI_RPC_PORT:-8080}"
PIN="${OMNI_PIN:-${KODI_UNLOCK_PIN:-}}"

post() {
  local auth=()
  [[ -n "${KODI_RPC_USER:-}" ]] && auth=(-u "$KODI_RPC_USER:${KODI_RPC_PASS:-}")
  curl -sS --max-time 10 "${auth[@]}" \
    -H 'Content-Type: application/json' -d "$1" \
    "http://$KODI_HOST:$KODI_RPC_PORT/jsonrpc"
  echo
}

notify() {
  post "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"JSONRPC.NotifyAll\",\"params\":{\"sender\":\"omnimessage-cli\",\"message\":\"$1\",\"data\":$2}}"
}

case "${1:-status}" in
  on|enable)
    notify enable '{}'
    ;;
  off|disable)
    notify disable "{\"pin\":\"$PIN\"}"
    ;;
  status)
    post '{"jsonrpc":"2.0","id":1,"method":"XBMC.GetInfoLabels","params":{"labels":["Window(Home).Property(omnimessage.enabled)","Window(Home).Property(omnimessage.blocking)","Window(Home).Property(omnimessage.unlocked)","Window(Home).Property(omnimessage.unlocked_seconds)"]}}'
    ;;
  *)
    echo "usage: $0 {on|off|status}" >&2
    exit 2
    ;;
esac
