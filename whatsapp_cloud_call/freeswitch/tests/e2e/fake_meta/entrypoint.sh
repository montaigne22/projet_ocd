#!/bin/sh
# Test only: the image of the call server started as a fake Meta (profile "meta", port 5081,
# event socket 127.0.0.1:8022, voice ports 40000-41000, on the same machine as the call server).
#   OCD_TEST_DOMAIN   name of the call server (default calls.ocd.test)
#   OCD_TEST_PROXY    where the calls go (default: the name, port 5061); the SIP stack of
#                     FreeSWITCH does not read /etc/hosts: an IP for a name of test
#   META_PASSWORD     SIP password of Meta (the one given to Odoo)
set -eu
CONF=/etc/freeswitch
cp -a /usr/share/freeswitch/conf/vanilla/. "$CONF/"
rm -rf "$CONF/sip_profiles/"* "$CONF/directory/default.xml" "$CONF/directory/default" "$CONF/skinny_profiles"
sed -i -E 's#<X-PRE-PROCESS cmd="stun-set" data="(external_(rtp|sip)_ip)=[^"]*"/>#<X-PRE-PROCESS cmd="set" data="\1=auto"/>#' "$CONF/vars.xml"
cp /usr/share/ocd/conf/autoload_configs/modules.conf.xml "$CONF/autoload_configs/"
cp /usr/share/ocd/conf/autoload_configs/local_stream.conf.xml "$CONF/autoload_configs/"
cp /opt/fake_meta/meta.xml "$CONF/sip_profiles/meta.xml"
sed -i 's#<!-- <param name="rtp-start-port" value="16384"/> -->#<param name="rtp-start-port" value="40000"/>#; s#<!-- <param name="rtp-end-port" value="32768"/> -->#<param name="rtp-end-port" value="41000"/>#' \
  "$CONF/autoload_configs/switch.conf.xml"
cat > "$CONF/autoload_configs/event_socket.conf.xml" <<EOF
<configuration name="event_socket.conf" description="Socket Client">
  <settings>
    <param name="listen-ip" value="127.0.0.1"/>
    <param name="listen-port" value="8022"/>
    <param name="password" value="meta-esl"/>
  </settings>
</configuration>
EOF
DOMAIN="${OCD_TEST_DOMAIN:-calls.ocd.test}"
PROXY="${OCD_TEST_PROXY:-$DOMAIN:5061}"
sed -i "s#</include>#  <X-PRE-PROCESS cmd=\"set\" data=\"ocd_test_domain=$DOMAIN\"/>\n  <X-PRE-PROCESS cmd=\"set\" data=\"ocd_test_proxy=$PROXY\"/>\n  <X-PRE-PROCESS cmd=\"set\" data=\"meta_password=${META_PASSWORD}\"/>\n</include>#" "$CONF/vars.xml"
mkdir -p "$CONF/tls" /tmp/meta
cp /run/ocd-certs/agent.pem "$CONF/tls/agent.pem"
cp /run/ocd-certs/cafile.pem "$CONF/tls/cafile.pem"
printf '[default]\nhost => 127.0.0.1\nport => 8022\npassword => meta-esl\n' > /etc/fs_cli.conf
exec /usr/bin/freeswitch -nonat -nf -nc -run /run/freeswitch -conf "$CONF" -log /var/log/freeswitch -db /var/lib/freeswitch/db
