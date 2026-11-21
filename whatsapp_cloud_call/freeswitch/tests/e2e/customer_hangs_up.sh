#!/bin/sh
# The customer hangs up while they talk with an agent: the agent must see it at once (fixed in
# 20.0.1.4.2: without the RTP clock of the profiles, the call server read the hang-up of Meta
# only when the agent hung up too). Without Odoo: the call server, a fake Meta (with RTCP, like
# Meta) and a fake agent (plain SIP), all from the image of the call server.
#   CERTS=<folder of agent.pem, cafile.pem> IP=<IP of the machine> sh customer_hangs_up.sh
# calls.ocd.test must point to IP in /etc/hosts. Prints when each side saw the end; the three
# times must be within a fraction of a second.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
IMAGE=${IMAGE:-ocd-freeswitch:1.11.3-ocd1}
WORK=$(mktemp -d)
cat > "$WORK/meta.xml" <<EOF
<include>
  <user id="+22890000001">
    <params><param name="password" value="meta-test-pw"/></params>
    <variables><variable name="user_context" value="ocd_whatsapp"/><variable name="ocd_trunk" value="1110001"/></variables>
  </user>
</include>
EOF
cat > "$WORK/agents.xml" <<EOF
<include>
  <user id="agent5">
    <params><param name="password" value="agent-test-pw"/></params>
    <variables><variable name="user_context" value="ocd_agents"/></variables>
  </user>
</include>
EOF
cat > "$WORK/settings.lua" <<EOF
return { odoo_url = "", domain = "calls.ocd.test", agents = { "agent5" },
         trunks = { ["1110001"] = { number = "22890000001", max_wait = 180, voicemail = true } } }
EOF
docker stop ocd-test-server ocd-test-meta ocd-test-agent >/dev/null 2>&1 || true
docker container prune -f >/dev/null
docker run -d --name ocd-test-server --network host -e OCD_SIP_DOMAIN=calls.ocd.test -e OCD_ESL_PASSWORD=test-esl \
  -e EXTERNAL_IP="$IP" -e OCD_AGENT_CANDIDATE_ACL=localnet.auto -v "$CERTS":/run/ocd-certs:ro "$IMAGE" >/dev/null
docker run -d --name ocd-test-meta --network host -e META_PASSWORD=meta-test-pw -e OCD_TEST_PROXY="$IP:5061" \
  -v "$CERTS":/run/ocd-certs:ro -v "$HERE/fake_meta":/opt/fake_meta:ro --entrypoint /opt/fake_meta/entrypoint.sh "$IMAGE" >/dev/null
sleep 15
docker cp "$WORK/meta.xml" ocd-test-server:/etc/freeswitch/directory/ocd/meta.xml
docker cp "$WORK/agents.xml" ocd-test-server:/etc/freeswitch/directory/ocd/agents.xml
docker cp "$WORK/settings.lua" ocd-test-server:/var/lib/freeswitch/ocd/settings.lua
docker exec ocd-test-server fs_cli -x reloadxml >/dev/null
docker run -d --name ocd-test-agent --network host -e OCD_AGENTS_PROXY="$IP:5090" -e AGENT_LOGIN=agent5 \
  -e AGENT_PASSWORD=agent-test-pw -v "$HERE/fake_agent":/opt/fake_agent:ro --entrypoint /opt/fake_agent/entrypoint.sh "$IMAGE" >/dev/null
sleep 12
docker exec ocd-test-meta fs_cli -x "bgapi originate {meta_name=hangup,meta_seconds=12,sip_h_x-wa-meta-wacid=wacid.HANGUP,sip_h_x-wa-meta-phone-number-id=1110001,origination_caller_id_number=+237670000000,rtp_secure_media=mandatory:AES_CM_128_HMAC_SHA1_80,absolute_codec_string=OPUS,rtcp_audio_interval_msec=1000,rtcp_mux=true}sofia/gateway/ocd/+22890000001 &lua(/opt/fake_meta/meta_call.lua)" >/dev/null
sleep 25
echo "the customer hangs up:"
docker exec ocd-test-meta sh -c 'grep -a "Sending BYE" /var/log/freeswitch/freeswitch.log' | cut -c38-120 | tail -1
echo "the call server sees it:"
docker exec ocd-test-server sh -c 'grep -aE "Hangup sofia/ocd_whatsapp|\[ocd\].*end:" /var/log/freeswitch/freeswitch.log' | cut -c1-200 | tail -2
echo "the agent sees it:"
docker exec ocd-test-agent sh -c 'grep -a "Hangup sofia" /var/log/freeswitch/freeswitch.log' | cut -c38-160 | tail -1
docker stop ocd-test-server ocd-test-meta ocd-test-agent >/dev/null
