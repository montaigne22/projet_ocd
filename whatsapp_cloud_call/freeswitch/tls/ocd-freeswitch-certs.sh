#!/bin/bash
# OCD: the certificate of the call server (Let's Encrypt) for FreeSWITCH and coturn.
#
#   ocd-freeswitch-certs.sh copy     deploy hook of certbot: copy the renewed certificate
#   ocd-freeswitch-certs.sh apply    daily (ocd-freeswitch-certs.timer, at night): FreeSWITCH and
#                                    coturn take the new certificate, only when no call is going on
#
# FreeSWITCH reads its certificate when a profile starts: restarting the profiles cuts the calls
# in progress, so it waits for a moment without calls (the certificate is renewed 30 days before
# its end: there is time).
#
# Settings in /etc/default/ocd-freeswitch-certs (optional):
#   OCD_MODE=native|docker       FreeSWITCH installed on the server (default) or in Docker
#   OCD_SIP_DOMAIN=...           name of the server (default: read in vars_ocd.xml, or in .env)
#   OCD_COMPOSE_FILE=...         Docker: the docker-compose.yml of the call server
#   OCD_CERTS_DIR=...            Docker: the folder of the certificate (OCD_CERTS_DIR of .env)
set -euo pipefail
[ -f /etc/default/ocd-freeswitch-certs ] && . /etc/default/ocd-freeswitch-certs

MODE="${OCD_MODE:-native}"
COMPOSE_FILE="${OCD_COMPOSE_FILE:-/opt/ocd-calls/docker/docker-compose.yml}"
COMPOSE_DIR="$(dirname "$COMPOSE_FILE")"
if [ "$MODE" = docker ] && [ -z "${OCD_CERTS_DIR:-}" ]; then
  OCD_CERTS_DIR="$(sed -n 's/^OCD_CERTS_DIR=//p' "$COMPOSE_DIR/.env" | head -1)"
fi
if [ -z "${OCD_SIP_DOMAIN:-}" ]; then
  if [ "$MODE" = docker ]; then
    OCD_SIP_DOMAIN="$(sed -n 's/^OCD_SIP_DOMAIN=//p' "$COMPOSE_DIR/.env" | head -1)"
  else
    OCD_SIP_DOMAIN="$(sed -n 's/.*ocd_sip_domain=\([^"]*\)".*/\1/p' /etc/freeswitch/vars_ocd.xml | head -1)"
  fi
fi
LIVE="${OCD_LIVE_DIR:-/etc/letsencrypt/live/$OCD_SIP_DOMAIN}"
STAMP=/var/lib/ocd-freeswitch-certs.applied

install_file() {
  # install_file <source> <target> <owner> <mode>
  install -o "${3%%:*}" -g "${3##*:}" -m "$4" "$1" "$2.new"
  mv "$2.new" "$2"
}

copy_native() {
  local certs=/etc/freeswitch/tls
  install -d -o freeswitch -g freeswitch -m 750 "$certs"
  cat "$LIVE/fullchain.pem" "$LIVE/privkey.pem" > "$certs/agent.pem.src"
  install_file "$certs/agent.pem.src" "$certs/agent.pem" freeswitch:freeswitch 640
  install_file "$certs/agent.pem.src" "$certs/wss.pem" freeswitch:freeswitch 640
  install_file "$LIVE/chain.pem" "$certs/cafile.pem" freeswitch:freeswitch 640
  rm -f "$certs/agent.pem.src"
  if id turnserver >/dev/null 2>&1; then
    install_file "$LIVE/fullchain.pem" /etc/coturn/ocd-fullchain.pem turnserver:turnserver 640
    install_file "$LIVE/privkey.pem" /etc/coturn/ocd-privkey.pem turnserver:turnserver 640
  fi
}

copy_docker() {
  # read by the containers as root at their start (FreeSWITCH copies it, coturn reads it)
  local certs="${OCD_CERTS_DIR:-$COMPOSE_DIR/data/certs}"
  case "$certs" in /*) ;; *) certs="$COMPOSE_DIR/${certs#./}" ;; esac
  install -d -o root -g root -m 750 "$certs"
  cat "$LIVE/fullchain.pem" "$LIVE/privkey.pem" > "$certs/agent.pem.src"
  install_file "$certs/agent.pem.src" "$certs/agent.pem" root:root 640
  install_file "$LIVE/chain.pem" "$certs/cafile.pem" root:root 640
  install_file "$LIVE/fullchain.pem" "$certs/fullchain.pem" root:root 640
  install_file "$LIVE/privkey.pem" "$certs/privkey.pem" root:root 640
  rm -f "$certs/agent.pem.src"
}

apply_native() {
  [ -f /etc/freeswitch/tls/agent.pem ] || exit 0
  if [ -f "$STAMP" ] && [ ! /etc/freeswitch/tls/agent.pem -nt "$STAMP" ]; then
    exit 0
  fi
  calls=$(fs_cli -x "show calls count" | grep -o '^[0-9]*' || echo 1)
  if [ "${calls:-1}" != "0" ]; then
    echo "Calls in progress: the certificate will be applied at the next run."
    exit 0
  fi
  fs_cli -x "sofia profile ocd_whatsapp restart"
  fs_cli -x "sofia profile ocd_agents restart"
  if systemctl is-active --quiet coturn; then
    systemctl restart coturn
  fi
  touch "$STAMP"
}

apply_docker() {
  local out
  out=$(docker compose -f "$COMPOSE_FILE" exec -T freeswitch ocd-freeswitch-healthcheck --reload-certs)
  echo "$out"
  if printf '%s' "$out" | grep -q "Certificate applied"; then
    docker compose -f "$COMPOSE_FILE" restart coturn
  fi
}

case "${1:-}" in
  copy) "copy_$MODE" ;;
  apply) "apply_$MODE" ;;
  *) echo "usage: $0 copy|apply" >&2; exit 2 ;;
esac
