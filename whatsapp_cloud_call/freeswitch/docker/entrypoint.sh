#!/bin/sh
# Start of the FreeSWITCH container of OCD: the configuration put together, then FreeSWITCH.
#
# Environment (docker/.env):
#   OCD_SIP_DOMAIN            name of the call server (its certificate is for this name), required
#   OCD_ESL_PASSWORD          password of the event socket (127.0.0.1:8021), required
#   EXTERNAL_IP               public IP of the server (else found by STUN)
#   OCD_SRTP                  SDES (default) or DTLS: encryption of the voice with Meta
#   OCD_AGENT_CANDIDATE_ACL   ICE candidates of the agents accepted (default wan_v4.auto)
#   OCD_RTP_START, OCD_RTP_END  UDP ports of the voice (default 16384-29999)
#
# The certificate (fullchain + key in agent.pem, as written by ocd-freeswitch-certs.sh) is read
# from /run/ocd-certs and copied for FreeSWITCH, which writes its own DTLS key next to it.
set -eu

CONF=/etc/freeswitch
OCD=/usr/share/ocd
STATE=/var/lib/freeswitch/ocd

: "${OCD_SIP_DOMAIN:?OCD_SIP_DOMAIN is missing: the name of the call server}"
: "${OCD_ESL_PASSWORD:?OCD_ESL_PASSWORD is missing: the password of the event socket}"

xml_value() {
  # a value for an XML attribute, without the characters that would break it
  printf '%s' "$1" | tr -d '"<>&\r\n'
}

# 1. the configuration of FreeSWITCH (once), then the files of OCD (at each start: a new image
#    brings its new files)
if [ ! -f "$CONF/freeswitch.xml" ]; then
  cp -a /usr/share/freeswitch/conf/vanilla/. "$CONF/"
fi
# no profile or user of the examples (their passwords are known to all)
rm -rf "$CONF/sip_profiles/internal.xml" "$CONF/sip_profiles/internal-ipv6.xml" \
  "$CONF/sip_profiles/external.xml" "$CONF/sip_profiles/external-ipv6.xml" \
  "$CONF/sip_profiles/internal" "$CONF/sip_profiles/external" "$CONF/sip_profiles/external-ipv6" \
  "$CONF/directory/default.xml" "$CONF/directory/default" "$CONF/skinny_profiles"
mkdir -p "$CONF/sip_profiles" "$CONF/dialplan" "$CONF/directory/ocd" "$CONF/autoload_configs" "$CONF/tls"
cp "$OCD/conf/vars_ocd.xml" "$CONF/vars_ocd.xml"
cp "$OCD/conf/sip_profiles/"*.xml "$CONF/sip_profiles/"
cp "$OCD/conf/dialplan/ocd.xml" "$CONF/dialplan/ocd.xml"
cp "$OCD/conf/directory/ocd.xml" "$CONF/directory/ocd.xml"
cp "$OCD/conf/autoload_configs/"*.xml "$CONF/autoload_configs/"
grep -q 'vars_ocd.xml' "$CONF/vars.xml" \
  || sed -i 's#</include>#  <X-PRE-PROCESS cmd="include" data="vars_ocd.xml"/>\n</include>#' "$CONF/vars.xml"
mkdir -p /usr/share/freeswitch/scripts
cp -r "$OCD/scripts/." /usr/share/freeswitch/scripts/

# 2. the settings of this server (read by vars_ocd.xml, after its own values)
mkdir -p "$STATE" /var/spool/ocd-calls/voicemail /var/spool/ocd-calls/cdr-errors
# a fixed public IP: no question to a STUN server at each reload of the configuration (the
# examples of FreeSWITCH ask stun.freeswitch.org, a server outside, each time)
if [ -n "${EXTERNAL_IP:-}" ]; then
  IP="$(xml_value "$EXTERNAL_IP")"
  sed -i -E "s#<X-PRE-PROCESS cmd=\"stun-set\" data=\"(external_(rtp|sip)_ip)=[^\"]*\"/>#<X-PRE-PROCESS cmd=\"set\" data=\"\\1=$IP\"/>#" "$CONF/vars.xml"
fi
# the ports of the voice: below 30000 by default, out of the ports of the NodePort services of
# Kubernetes (30000-32767, k3s on the same machine)
RTP_START="${OCD_RTP_START:-16384}"
RTP_END="${OCD_RTP_END:-29999}"
case "$RTP_START$RTP_END" in
  *[!0-9]*) echo "OCD_RTP_START and OCD_RTP_END are port numbers" >&2; exit 1 ;;
esac
sed -i -E \
  -e "s#(<!-- *)?<param name=\"rtp-start-port\" value=\"[0-9]*\"/>( *-->)?#<param name=\"rtp-start-port\" value=\"$RTP_START\"/>#" \
  -e "s#(<!-- *)?<param name=\"rtp-end-port\" value=\"[0-9]*\"/>( *-->)?#<param name=\"rtp-end-port\" value=\"$RTP_END\"/>#" \
  "$CONF/autoload_configs/switch.conf.xml"
case "${OCD_SRTP:-SDES}" in
  DTLS|dtls) SRTP="optional:AES_CM_128_HMAC_SHA1_80" ;;
  *) SRTP="mandatory:AES_CM_128_HMAC_SHA1_80:AES_CM_128_HMAC_SHA1_32" ;;
esac
cat > "$STATE/vars_env.xml" <<EOF
<include>
  <X-PRE-PROCESS cmd="set" data="ocd_sip_domain=$(xml_value "$OCD_SIP_DOMAIN")"/>
  <X-PRE-PROCESS cmd="set" data="ocd_esl_password=$(xml_value "$OCD_ESL_PASSWORD")"/>
  <X-PRE-PROCESS cmd="set" data="ocd_srtp=$SRTP"/>
  <X-PRE-PROCESS cmd="set" data="ocd_agent_candidate_acl=$(xml_value "${OCD_AGENT_CANDIDATE_ACL:-wan_v4.auto}")"/>
</include>
EOF
chmod 640 "$STATE/vars_env.xml"
# fs_cli (healthcheck, docker compose exec freeswitch fs_cli) with the password of the event socket
printf '[default]\npassword => %s\n' "$OCD_ESL_PASSWORD" > /etc/fs_cli.conf
chmod 600 /etc/fs_cli.conf

# 3. the certificate
/usr/local/bin/ocd-freeswitch-healthcheck --copy-certs || true
if [ ! -s "$CONF/tls/agent.pem" ]; then
  echo "WARNING: no certificate in /run/ocd-certs (agent.pem): the profiles in TLS do not start." >&2
fi

# 4. the files belong to FreeSWITCH (the certificates mounted read-only are left as they are)
chown -R freeswitch:freeswitch "$CONF" /var/lib/freeswitch /var/log/freeswitch /var/spool/ocd-calls \
  /run/freeswitch /usr/share/freeswitch/scripts

exec /usr/bin/freeswitch -u freeswitch -g freeswitch -nonat -nf -nc \
  -run /run/freeswitch -conf /etc/freeswitch -log /var/log/freeswitch -db /var/lib/freeswitch/db
