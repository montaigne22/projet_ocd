-- An agent calls a customer (the company calls; dialled out<ID of the call in Odoo> from the
-- phone of the top bar). Odoo says whom and through which WhatsApp number, and refuses what it
-- did not prepare: without its answer, no call (a call of the company is paid). The customer is
-- called through the gateway to Meta (meta_<phone number ID>); the agent hears it ring, then the
-- customer. The end is told to Odoo.
package.path = "/usr/share/freeswitch/scripts/?.lua;" .. package.path

local queue = require("ocd.queue")
local odoo = require("ocd.odoo")

local settings = odoo.load_settings()
local uuid = session:get_uuid()

local function log(level, text)
  freeswitch.consoleLog(level, "[ocd] " .. uuid .. " " .. text .. "\n")
end

local function var(name)
  local value = session:getVariable(name)
  if value == nil or value == "" or value == "_undef_" then
    return nil
  end
  return value
end

local function setvar(name, value)
  session:setVariable(name, tostring(value))
end

local call_id = queue.safe(var("ocd_call") or "", 16)
local agent = queue.safe(var("sip_auth_username") or var("sip_from_user") or "", 32)

local code, body = odoo.post(settings, "/whatsapp/call/server/outbound", {
  { "call", call_id }, { "agent", agent }, { "uuid", uuid },
}, 3)
local answer = code == 200 and queue.parse_lines(body) or {}
local number = queue.digits(answer.number)
local pnid = queue.safe(answer.phone_number_id or "", 32)
if number == "" or pnid == "" then
  local reason = queue.safe_name(answer.error or (code == 0 and "Odoo does not answer" or "Refused by Odoo"))
  log("WARNING", "outbound call " .. call_id .. " of " .. agent .. " refused: " .. reason)
  session:execute("respond", "403 " .. reason)
  return
end

setvar("ocd_outbound", 1)
setvar("ocd_from", number)
setvar("ocd_pnid", pnid)
setvar("ocd_outcome", "missed")
setvar("ocd_ended_by", "agent")
setvar("ocd_talk", 0)
setvar("hangup_after_bridge", "false")
setvar("continue_on_fail", "true")
-- the agent hears it ring until the customer picks up (or what Meta sends meanwhile)
setvar("ringback", "%(1500,3500,440)")
setvar("instant_ringback", "true")
log("NOTICE", "outbound call " .. call_id .. " of " .. agent .. " to +" .. number .. " through meta_" .. pnid)

local srtp = answer.srtp == "DTLS" and "optional:AES_CM_128_HMAC_SHA1_80"
  or "mandatory:AES_CM_128_HMAC_SHA1_80:AES_CM_128_HMAC_SHA1_32"
local ring = tonumber(answer.max_ring) or 45
local started = os.time()
session:execute("bridge", "{ignore_early_media=false}[" .. table.concat({
  "leg_timeout=" .. ring,
  "absolute_codec_string=OPUS",
  "rtp_secure_media=" .. srtp,
  "origination_caller_id_number=+" .. queue.digits(answer.business_number),
  "api_on_answer=luarun ocd_whatsapp_event.lua outbound_answered " .. uuid .. " " .. agent,
}, ",") .. "]sofia/gateway/meta_" .. pnid .. "/+" .. number)

local answered = var("ocd_customer_answered") == "1"
local cause = var("last_bridge_hangup_cause")
  or (answered and "NORMAL_CLEARING" or var("originate_failed_cause") or var("originate_disposition"))
local agent_up = session:ready()
local outcome, ended_by = queue.outbound_end({ answered = answered, agent_up = agent_up, cause = cause })
local talk = 0
if answered then
  talk = math.max(0, os.time() - (tonumber(var("ocd_answer_epoch") or "") or os.time()))
end
log("NOTICE", "end: " .. outcome .. ", ended by " .. ended_by .. ", cause " .. tostring(cause or "none") ..
    ", talk " .. talk .. " s")
setvar("ocd_outcome", outcome)
setvar("ocd_ended_by", ended_by)
setvar("ocd_talk", talk)
if agent_up then
  session:hangup(answered and "NORMAL_CLEARING" or (cause or "NORMAL_CLEARING"))
end
odoo.event(settings, {
  event = "ended", call = call_id, uuid = uuid, agent = agent, outcome = outcome,
  ended_by = ended_by, talk = talk, wait = os.time() - started - talk, cause = cause,
  number = number, phone_number_id = pnid,
})
