-- The script of the queue (ocd_whatsapp_inbound.lua) run with a fake FreeSWITCH and a fake Odoo:
-- whole calls, from the INVITE of Meta to the end.
--   lua5.3 whatsapp_cloud_call/freeswitch/tests/test_inbound.lua
local here = arg[0]:match("^(.*)/tests/[^/]+$") or "."
package.path = here .. "/scripts/?.lua;" .. package.path
local queue = require("ocd.queue")

local failures, count = 0, 0
local function check(name, condition)
  count = count + 1
  if not condition then
    failures = failures + 1
    print("FAIL: " .. name)
  end
end

local tmp = os.tmpname()
os.remove(tmp)
os.execute("mkdir -p " .. tmp .. "/voicemail")

-- a call: registered agents, what each bridge does, what Odoo answers
local function run(scenario)
  local clock = 1000
  local real_time = os.time
  os.time = function() return clock end
  local vars = {
    sip_from_user = "+237670000000",
    sip_to_user = "+22890000001",
    ["sip_h_x-wa-meta-wacid"] = "wacid.TEST",
    ["sip_h_x-wa-meta-phone-number-id"] = "1110001",
  }
  for key, value in pairs(scenario.vars or {}) do
    vars[key] = value ~= false and value or nil
  end
  local up = true
  local log = { bridges = {}, events = {}, voicemails = {}, played = {} }
  local bridge_index = 0

  local session = {}
  function session:get_uuid() return "uuid-a" end
  function session:getVariable(name) return vars[name] end
  function session:setVariable(name, value) vars[name] = value end
  function session:setAutoHangup() end
  function session:answer() log.answered = true end
  function session:ready() return up end
  function session:hangup(cause) up = false; log.hangup = cause end
  function session:recordFile(path, max, threshold, silence)
    log.recorded = path
    local file = io.open(path, "wb")
    file:write(string.rep("\0", scenario.voicemail_size or 32000))
    file:close()
    clock = clock + 20
    if scenario.hangup_after_record then up = false end
  end
  function session:execute(app, data)
    if app == "bridge" then
      bridge_index = bridge_index + 1
      log.bridges[#log.bridges + 1] = data
      local step = (scenario.bridges or {})[bridge_index] or {}
      clock = clock + (step.seconds or 20)
      if step.answer then
        vars.ocd_round_agent = step.answer
        vars.ocd_answer_epoch = tostring(clock - (step.talk or 0))
      end
      vars.last_bridge_hangup_cause = step.cause
      vars.originate_disposition = step.answer and "SUCCESS" or (step.disposition or "NO_ANSWER")
      if step.customer_hangs_up then up = false end
      if step.unregister then scenario.registered[step.unregister] = nil end
    elseif app == "playback" then
      log.played[#log.played + 1] = data
      if data == "local_stream://moh" then clock = clock + 5 end
    elseif app == "set" then
      local key, value = data:match("^([^=]+)=(.*)$")
      vars[key] = value
    end
  end
  _G.session = session
  _G.freeswitch = {
    API = function()
      return {
        execute = function(_, command, args)
          if command == "sofia_contact" then
            local agent = args:match("/(agent%d+)@")
            return scenario.registered[agent] and ("sofia/ocd_agents/" .. agent) or "error/user_not_registered"
          end
          return "+OK"
        end,
        executeString = function() return "+OK" end,
      }
    end,
    consoleLog = function(_, text) log.console = (log.console or "") .. text end,
  }
  package.loaded["ocd.odoo"] = {
    load_settings = function()
      return {
        odoo_url = "", headers_file = "", domain = "calls.example.com", spool = tmp,
        sounds = tmp .. "/sounds", hold_music = "local_stream://moh",
        agents = { "agent5", "agent7" }, trunks = { ["1110001"] = { max_wait = 180, voicemail = true } },
      }
    end,
    route = function(_, call) log.route_call = call; return scenario.odoo_route end,
    event = function(_, values)
      values.customer_up = up
      log.events[#log.events + 1] = values
      return true
    end,
    voicemail = function(_, path, values) log.voicemails[#log.voicemails + 1] = values; return scenario.voicemail_ok ~= false end,
  }
  local chunk = assert(loadfile(here .. "/scripts/ocd_whatsapp_inbound.lua"))
  local ok, err = pcall(chunk)
  os.time = real_time
  log.error = not ok and err or nil
  log.vars = vars
  return log
end

local function last_event(log, kind)
  for i = #log.events, 1, -1 do
    if log.events[i].event == kind then return log.events[i] end
  end
end

-- 1. the agent of the conversation answers, then hangs up
local log = run({
  registered = { agent5 = true, agent7 = true },
  odoo_route = queue.parse_lines("call=12\nname=Awa Ngono\nfirst=agent7\nagents=agent7,agent5\nmax_wait=180\nvoicemail=1\nopen=1\n"),
  bridges = { { answer = "agent7", talk = 95, cause = "NORMAL_CLEARING", seconds = 100 } },
})
check("1 no error " .. tostring(log.error), not log.error)
check("1 answered at once", log.answered)
check("1 the agent of the conversation alone first", log.bridges[1]:find("user/agent7@", 1, true) and not log.bridges[1]:find("agent5", 1, true))
check("1 the call of Odoo on the agent's phone", log.bridges[1]:find("sip_h_X-OCD-Call=12", 1, true) ~= nil)
local ended = last_event(log, "ended")
check("1 ended completed by the agent", ended and ended.outcome == "completed" and ended.ended_by == "agent")
check("1 agent and talk time", ended.agent == "agent7" and ended.talk == 95)
check("1 variables for the record", log.vars.ocd_outcome == "completed" and log.vars.ocd_wacid == "wacid.TEST" and log.vars.ocd_from == "237670000000")
check("1 hung up", log.hangup == "NORMAL_CLEARING")

-- 2. the agent is cut off, reconnects and gets the call back
log = run({
  registered = { agent5 = true, agent7 = true },
  odoo_route = queue.parse_lines("call=13\nagents=agent5,agent7\nfirst=\n"),
  bridges = {
    { answer = "agent5", talk = 30, cause = "MEDIA_TIMEOUT", seconds = 40 },
    { answer = "agent5", talk = 60, cause = "NORMAL_CLEARING", seconds = 70 },
  },
})
check("2 no error " .. tostring(log.error), not log.error)
check("2 two bridges", #log.bridges == 2)
check("2 everyone first", log.bridges[1]:find("agent7", 1, true) ~= nil)
check("2 the agent cut off alone after", log.bridges[2]:find("user/agent5@", 1, true) and not log.bridges[2]:find("agent7", 1, true))
check("2 agent lost told to Odoo", last_event(log, "agent_lost") and last_event(log, "agent_lost").agent == "agent5")
ended = last_event(log, "ended")
check("2 ended completed with 1 reconnection", ended.outcome == "completed" and ended.reconnects == 1 and ended.talk == 90)

-- 3. Odoo does not answer, nobody is connected: voicemail after 30 seconds
log = run({ registered = {}, odoo_route = nil, voicemail_size = 64000 })
check("3 no error " .. tostring(log.error), not log.error)
check("3 nobody rang", #log.bridges == 0)
check("3 recorded", log.recorded == tmp .. "/voicemail/uuid-a.wav")
check("3 voicemail sent", #log.voicemails == 1 and log.voicemails[1].wacid == "wacid.TEST")
check("3 file removed once sent", io.open(log.recorded, "rb") == nil)
ended = last_event(log, "ended")
check("3 ended voicemail by the system", ended.outcome == "voicemail" and ended.ended_by == "system")
check("3 waited about 30 seconds", ended.wait >= 30 and ended.wait < 60)

-- 4. voicemail not sent (Odoo down): kept with its facts for ocd-call-sync
log = run({ registered = {}, odoo_route = nil, voicemail_ok = false })
local kept = io.open(tmp .. "/voicemail/uuid-a.wav", "rb")
local facts = io.open(tmp .. "/voicemail/uuid-a.txt", "r")
check("4 kept for later", kept ~= nil and facts ~= nil)
check("4 facts", facts and facts:read("*a"):find("wacid=wacid.TEST", 1, true) ~= nil)
if kept then kept:close() end
os.remove(tmp .. "/voicemail/uuid-a.wav")
os.remove(tmp .. "/voicemail/uuid-a.txt")

-- 5. the customer hangs up while the agents ring: missed, no voicemail
log = run({
  registered = { agent5 = true },
  odoo_route = queue.parse_lines("call=14\nagents=agent5\n"),
  bridges = { { seconds = 15, customer_hangs_up = true } },
})
check("5 no error " .. tostring(log.error), not log.error)
ended = last_event(log, "ended")
check("5 missed, ended by the customer", ended.outcome == "missed" and ended.ended_by == "customer")
check("5 no voicemail", log.recorded == nil)

-- 6. agents ring without answer until the waiting time: voicemail
log = run({
  registered = { agent5 = true },
  odoo_route = queue.parse_lines("call=15\nagents=agent5\nmax_wait=60\n"),
  bridges = { { seconds = 20 }, { seconds = 20 }, { seconds = 20 }, { seconds = 20 } },
})
check("6 no error " .. tostring(log.error), not log.error)
check("6 rang until the waiting time", #log.bridges == 3)
check("6 voicemail", last_event(log, "ended").outcome == "voicemail")

-- 7. the watch ended the leg of an agent gone (page closed): the colleague rings at once
log = run({
  registered = { agent5 = true, agent7 = true },
  odoo_route = queue.parse_lines("call=16\nagents=agent5,agent7\nfirst=agent5\n"),
  bridges = {
    { answer = "agent5", talk = 20, cause = "NETWORK_OUT_OF_ORDER", seconds = 30, unregister = "agent5" },
    { answer = "agent7", talk = 40, cause = "NORMAL_CLEARING", seconds = 45 },
  },
})
check("7 no error " .. tostring(log.error), not log.error)
check("7 the colleague rang right after", #log.bridges == 2 and log.bridges[2]:find("user/agent7@", 1, true) ~= nil)
ended = last_event(log, "ended")
check("7 completed by the colleague, 1 reconnection", ended.outcome == "completed" and ended.agent == "agent7" and ended.reconnects == 1)

-- 8. what Meta sent, in the log
log = run({
  registered = { agent5 = true },
  odoo_route = queue.parse_lines("call=17\nagents=agent5\n"),
  vars = { sip_network_ip = "157.240.1.1", sip_auth_username = "22890000001",
           rtp_use_codec_name = "opus", rtp_has_crypto = "AES_CM_128_HMAC_SHA1_80" },
  bridges = { { answer = "agent5", talk = 10, cause = "NORMAL_CLEARING", seconds = 12 } },
})
check("8 no error " .. tostring(log.error), not log.error)
check("8 the call in the log", (log.console or ""):find(
  "call of +237670000000 to +22890000001, phone number id 1110001, wacid wacid.TEST, from 157.240.1.1, signed as 22890000001",
  1, true) ~= nil)
check("8 codec and SRTP in the log", (log.console or ""):find("answered: codec opus, SRTP AES_CM_128_HMAC_SHA1_80", 1, true) ~= nil)
check("8 the end in the log", (log.console or ""):find("end: completed, ended by agent, cause NORMAL_CLEARING, hang-up sent to Meta", 1, true) ~= nil)
check("8 the customer let go before Odoo is told", last_event(log, "ended").customer_up == false and log.hangup == "NORMAL_CLEARING")
check("8 the number to Odoo", log.route_call.number == "237670000000" and log.route_call.user_ref == "")

-- 9. a customer who hides their number behind a WhatsApp username: their BSUID
log = run({
  registered = {},
  odoo_route = nil,
  vars = { sip_from_user = "CM.1349120865530", ["sip_h_x-wa-meta-user-id"] = false },
})
check("9 no error " .. tostring(log.error), not log.error)
check("9 no number, the BSUID to Odoo", log.route_call.number == "" and log.route_call.user_ref == "CM.1349120865530")
ended = last_event(log, "ended")
check("9 the BSUID in the end", ended.number == "" and ended.user_ref == "CM.1349120865530")
check("9 the BSUID in the record", log.vars.ocd_user_ref == "CM.1349120865530" and log.vars.ocd_from == "")
check("9 the BSUID in the log", (log.console or ""):find("call of user CM.1349120865530", 1, true) ~= nil)

-- 10. the number and the BSUID header of Meta
log = run({
  registered = {},
  odoo_route = nil,
  vars = { ["sip_h_x-wa-meta-user-id"] = "CM.77" },
})
check("10 the number and the BSUID", log.route_call.number == "237670000000" and log.route_call.user_ref == "CM.77")

os.execute("rm -rf " .. tmp)
print(string.format("%d checks, %d failures", count, failures))
os.exit(failures == 0 and 0 or 1)
