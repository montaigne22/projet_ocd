#!/bin/sh
# Test only: the image of the call server started as an agent who signs in to the call server in
# plain SIP (UDP, port 5090), answers every call and sends a tone until the call ends.
#   OCD_TEST_DOMAIN   name of the call server (default calls.ocd.test)
#   OCD_AGENTS_PROXY  IP:5090 of the call server
#   AGENT_LOGIN, AGENT_PASSWORD  the agent, as in directory/ocd/agents.xml of the call server
set -eu
CONF=/etc/freeswitch
cp -a /usr/share/freeswitch/conf/vanilla/. "$CONF/"
mv "$CONF/sip_profiles" /tmp/vanilla_sip_profiles
mkdir "$CONF/sip_profiles"
sed -i -E 's#<X-PRE-PROCESS cmd="stun-set" data="(external_(rtp|sip)_ip)=[^"]*"/>#<X-PRE-PROCESS cmd="set" data="\1=auto"/>#' "$CONF/vars.xml"
cat > /tmp/vars_agent.xml <<EOF
  <X-PRE-PROCESS cmd="set" data="ocd_test_domain=${OCD_TEST_DOMAIN:-calls.ocd.test}"/>
  <X-PRE-PROCESS cmd="set" data="ocd_agents_proxy=${OCD_AGENTS_PROXY}"/>
  <X-PRE-PROCESS cmd="set" data="agent_login=${AGENT_LOGIN}"/>
  <X-PRE-PROCESS cmd="set" data="agent_password=${AGENT_PASSWORD}"/>
</include>
EOF
sed -i '$d' "$CONF/vars.xml"
cat /tmp/vars_agent.xml >> "$CONF/vars.xml"
cp /usr/share/ocd/conf/autoload_configs/modules.conf.xml "$CONF/autoload_configs/"
cp /opt/fake_agent/agent.xml "$CONF/sip_profiles/agent.xml"
cp /opt/fake_agent/dialplan.xml "$CONF/dialplan/agent.xml"
sed -i 's#<!-- <param name="rtp-start-port" value="16384"/> -->#<param name="rtp-start-port" value="42000"/>#; s#<!-- <param name="rtp-end-port" value="32768"/> -->#<param name="rtp-end-port" value="43000"/>#' "$CONF/autoload_configs/switch.conf.xml"
cat > "$CONF/autoload_configs/event_socket.conf.xml" <<EOF
<configuration name="event_socket.conf" description="Socket Client">
  <settings>
    <param name="listen-ip" value="127.0.0.1"/>
    <param name="listen-port" value="8023"/>
    <param name="password" value="agent-esl"/>
  </settings>
</configuration>
EOF
printf '[default]\nhost => 127.0.0.1\nport => 8023\npassword => agent-esl\n' > /etc/fs_cli.conf
exec /usr/bin/freeswitch -nonat -nf -nc -run /run/freeswitch -conf "$CONF" -log /var/log/freeswitch -db /var/lib/freeswitch/db
