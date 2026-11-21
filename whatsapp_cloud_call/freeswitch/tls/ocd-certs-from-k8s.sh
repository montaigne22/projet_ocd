#!/bin/bash
# OCD: the certificate of the call server taken from a Kubernetes secret (cert-manager in k3s),
# for a call server on a machine where Traefik holds the ports 80 and 443.
#
#   ocd-certs-from-k8s.sh      daily, before ocd-freeswitch-certs.sh apply (cron or timer)
#
# cert-manager keeps the certificate in a secret of type kubernetes.io/tls (tls.crt: certificate
# and chain, tls.key: key). This script writes them as certbot would (fullchain.pem, privkey.pem,
# chain.pem) in OCD_LIVE_DIR, and when they changed, runs "ocd-freeswitch-certs.sh copy"; the
# nightly "apply" then gives them to FreeSWITCH and coturn when no call is going on.
#
# Settings in /etc/default/ocd-freeswitch-certs:
#   OCD_K8S_SECRET=appels-ocdlive-tls     name of the secret (Certificate of cert-manager)
#   OCD_K8S_NAMESPACE=ocd                 its namespace
#   OCD_LIVE_DIR=/etc/ocd-calls/live      where to write the files (the same for the copy)
#   KUBECONFIG=/etc/rancher/k3s/k3s.yaml  default of k3s
set -euo pipefail
[ -f /etc/default/ocd-freeswitch-certs ] && . /etc/default/ocd-freeswitch-certs

SECRET="${OCD_K8S_SECRET:?OCD_K8S_SECRET missing in /etc/default/ocd-freeswitch-certs}"
NAMESPACE="${OCD_K8S_NAMESPACE:-default}"
LIVE="${OCD_LIVE_DIR:-/etc/ocd-calls/live}"
KUBECTL="${OCD_KUBECTL:-kubectl}"
export KUBECONFIG="${KUBECONFIG:-/etc/rancher/k3s/k3s.yaml}"
HERE="$(cd "$(dirname "$0")" && pwd)"

install -d -m 700 "$LIVE"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

$KUBECTL -n "$NAMESPACE" get secret "$SECRET" -o 'jsonpath={.data.tls\.crt}' | base64 -d > "$tmp/fullchain.pem"
$KUBECTL -n "$NAMESPACE" get secret "$SECRET" -o 'jsonpath={.data.tls\.key}' | base64 -d > "$tmp/privkey.pem"
if ! grep -q "BEGIN CERTIFICATE" "$tmp/fullchain.pem" || ! grep -q "PRIVATE KEY" "$tmp/privkey.pem"; then
  echo "The secret $NAMESPACE/$SECRET holds no certificate and key." >&2
  exit 1
fi
# the chain: the certificates after the first one
awk 'found { print } /END CERTIFICATE/ && !found { found = 1 }' "$tmp/fullchain.pem" > "$tmp/chain.pem"
[ -s "$tmp/chain.pem" ] || cp "$tmp/fullchain.pem" "$tmp/chain.pem"

if cmp -s "$tmp/fullchain.pem" "$LIVE/fullchain.pem" && cmp -s "$tmp/privkey.pem" "$LIVE/privkey.pem"; then
  exit 0
fi
for name in fullchain.pem privkey.pem chain.pem; do
  install -m 600 "$tmp/$name" "$LIVE/$name"
done
echo "New certificate from $NAMESPACE/$SECRET"
OCD_LIVE_DIR="$LIVE" "$HERE/ocd-freeswitch-certs.sh" copy
