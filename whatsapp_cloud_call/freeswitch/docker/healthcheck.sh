#!/bin/sh
# FreeSWITCH of OCD, in its container:
#   ocd-freeswitch-healthcheck                 healthy: FreeSWITCH up, both profiles running
#   ocd-freeswitch-healthcheck --copy-certs    copy the certificate of /run/ocd-certs (at the start)
#   ocd-freeswitch-healthcheck --reload-certs  copy it and restart the profiles, only when no
#                                              call is going on (after a renewal, at night)
set -u
CERTS_IN=/run/ocd-certs
CERTS=/etc/freeswitch/tls

copy_certs() {
  [ -s "$CERTS_IN/agent.pem" ] || return 1
  mkdir -p "$CERTS"
  changed=1
  for name in agent.pem wss.pem cafile.pem; do
    source="$CERTS_IN/$name"
    [ "$name" = wss.pem ] && [ ! -s "$source" ] && source="$CERTS_IN/agent.pem"
    [ -s "$source" ] || continue
    if ! cmp -s "$source" "$CERTS/$name"; then
      cp "$source" "$CERTS/$name.new" && chmod 640 "$CERTS/$name.new" && mv "$CERTS/$name.new" "$CERTS/$name"
      changed=0
    fi
  done
  chown -R freeswitch:freeswitch "$CERTS" 2>/dev/null || true
  return $changed
}

case "${1:-}" in
  --copy-certs)
    copy_certs
    exit 0
    ;;
  --reload-certs)
    calls=$(fs_cli -x "show calls count" 2>/dev/null | grep -o '^[0-9]*' | head -1)
    if [ "${calls:-1}" != "0" ]; then
      echo "Calls in progress: the certificate will be applied at the next run."
      exit 0
    fi
    if copy_certs; then
      fs_cli -x "sofia profile ocd_whatsapp restart"
      fs_cli -x "sofia profile ocd_agents restart"
      echo "Certificate applied."
    else
      echo "Certificate unchanged."
    fi
    exit 0
    ;;
esac

fs_cli -x status 2>/dev/null | grep -q '^UP' || exit 1
profiles=$(fs_cli -x "sofia status" 2>/dev/null)
for profile in ocd_whatsapp ocd_agents; do
  printf '%s\n' "$profiles" | grep -Eq "^[[:space:]]*$profile[[:space:]]+profile[[:space:]].*RUNNING" || exit 1
done
exit 0
