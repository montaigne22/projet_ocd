#!/bin/sh
# For the build only. When a CA is given as the BuildKit secret "build_ca" (a proxy that
# intercepts TLS), apt goes through HTTPS with it and git trusts it. Without it, nothing changes.
# apt reads it as its own user: a readable copy, removed by "build_ca_done".
if [ -s /run/secrets/build_ca ]; then
  install -m 644 /run/secrets/build_ca /etc/apt/build_ca.crt
  sed -i 's#http://deb.debian.org#https://deb.debian.org#g' /etc/apt/sources.list.d/debian.sources
  echo 'Acquire::https::CAInfo "/etc/apt/build_ca.crt";' > /etc/apt/apt.conf.d/99build-ca
  export GIT_SSL_CAINFO=/etc/apt/build_ca.crt
  export CURL_CA_BUNDLE=/etc/apt/build_ca.crt
fi
build_ca_done() {
  rm -f /etc/apt/build_ca.crt /etc/apt/apt.conf.d/99build-ca
}
