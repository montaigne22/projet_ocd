#!/bin/bash
# OCD: the certificate of the call server for FreeSWITCH (Let's Encrypt).
#
#   ocd-freeswitch-certs.sh copy     deploy hook of certbot: copy the renewed certificate
#   ocd-freeswitch-certs.sh apply    daily (ocd-freeswitch-certs.timer, at night): the profiles
#                                    take the new certificate, only when no call is going on
#
# FreeSWITCH reads its certificates when a profile starts: restarting the profiles cuts the
# calls in progress, so it waits for a moment without calls (the certificate is renewed 30
# days before its end: there is time).
set -euo pipefail
HOST="${OCD_SIP_DOMAIN:-$(sed -n 's/.*ocd_sip_domain=\([^"]*\)".*/\1/p' /etc/freeswitch/vars_ocd.xml | head -1)}"
LIVE="/etc/letsencrypt/live/$HOST"
CERTS=/etc/freeswitch/tls
STAMP=/var/lib/freeswitch/ocd/certs-applied

copy() {
  install -d -o freeswitch -g freeswitch -m 750 "$CERTS"
  cat "$LIVE/fullchain.pem" "$LIVE/privkey.pem" > "$CERTS/agent.pem.new"
  cp "$CERTS/agent.pem.new" "$CERTS/wss.pem.new"
  cp "$LIVE/chain.pem" "$CERTS/cafile.pem.new"
  for name in agent.pem wss.pem cafile.pem; do
    chown freeswitch:freeswitch "$CERTS/$name.new"
    chmod 640 "$CERTS/$name.new"
    mv "$CERTS/$name.new" "$CERTS/$name"
  done
  # the TURN relay (coturn) reads its own copy
  if id turnserver >/dev/null 2>&1; then
    install -o turnserver -g turnserver -m 640 "$LIVE/fullchain.pem" /etc/coturn/ocd-fullchain.pem
    install -o turnserver -g turnserver -m 640 "$LIVE/privkey.pem" /etc/coturn/ocd-privkey.pem
  fi
}

apply() {
  [ -f "$CERTS/agent.pem" ] || exit 0
  if [ -f "$STAMP" ] && [ ! "$CERTS/agent.pem" -nt "$STAMP" ]; then
    exit 0
  fi
  calls=$(fs_cli -x "show calls count" | grep -o '^[0-9]*' || echo 1)
  if [ "${calls:-1}" != "0" ]; then
    echo "Calls in progress: the certificate will be applied at the next run"
    exit 0
  fi
  fs_cli -x "sofia profile ocd_whatsapp restart"
  fs_cli -x "sofia profile ocd_agents restart"
  if systemctl is-active --quiet coturn; then
    systemctl restart coturn
  fi
  touch "$STAMP"
}

case "${1:-}" in
  copy) copy ;;
  apply) apply ;;
  *) echo "usage: $0 copy|apply" >&2; exit 2 ;;
esac
