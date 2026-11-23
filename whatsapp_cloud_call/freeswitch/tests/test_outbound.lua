-- The script of the calls of the company (ocd_whatsapp_outbound.lua) run with a fake FreeSWITCH
-- and a fake Odoo: the agent calls a customer through Meta.
--   lua5.3 whatsapp_cloud_call/freeswitch/tests/test_outbound.lua
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

-- a call: what Odoo answers, what the bridge to Meta does
local function run(scenario)
  local clock = 1000
  local real_time = os.time
  os.time = function() return clock end
  local vars = { ocd_call = "42", sip_auth_username = "agent5" }
  local up = true
  local log = { bridges = {}, events = {}, responds = {} }

  local session = {}
  function session:get_uuid() return "uuid-out" end
  function session:getVariable(name) return vars[name] end
  function session:setVariable(name, value) vars[name] = value end
  function session:ready() return up end
  function session:hangup(cause) up = false; log.hangup = cause end
  function session:execute(app, data)
    if app == "bridge" then
      log.bridges[#log.bridges + 1] = data
      local step = scenario.bridge or {}
      clock = clock + (step.ring or 10)
      if step.answer then
        vars.ocd_customer_answered = "1"
        vars.ocd_answer_epoch = tostring(clock)
        clock = clock + (step.talk or 0)
      end
      vars.last_bridge_hangup_cause = step.cause
      vars.originate_disposition = step.answer and "SUCCESS" or step.cause
      if step.agent_hangs_up then up = false; vars.sip_reason = step.agent_reason end
    elseif app == "respond" then
      log.responds[#log.responds + 1] = data
      up = false
    end
  end
  _G.session = session
  _G.freeswitch = {
    API = function() return { execute = function() return "+OK" end, executeString = function() return "+OK" end } end,
    consoleLog = function(_, text) log.console = (log.console or "") .. text end,
  }
  package.loaded["ocd.odoo"] = {
    load_settings = function() return { odoo_url = "https://odoo.example.com", domain = "calls.example.com" } end,
    post = function(_, path, fields)
      log.asked = { path = path, fields = fields }
      return scenario.odoo_code or 200, scenario.odoo_body or ""
    end,
    event = function(_, values) log.events[#log.events + 1] = values; return true end,
    sound = function(_, name) return (scenario.sounds or {})[name] end,
    recording_start = function(_, _settings, id)
      log.recording = { bridges = #log.bridges, uuid = id }
      return "/spool/recordings/" .. id .. ".wav"
    end,
    recording_facts = function(path, values) log.recording_facts = { path = path, values = values } end,
  }
  local chunk = assert(loadfile(here .. "/scripts/ocd_whatsapp_outbound.lua"))
  local ok, err = pcall(chunk)
  os.time = real_time
  log.error = not ok and err or nil
  log.vars = vars
  return log
end

local ALLOWED = "number=237670000000\nphone_number_id=1110001\nbusiness_number=22890000001\nsrtp=SDES\nmax_ring=45\n"
local ALLOWED_30 = ALLOWED .. "max_talk=1800\n"

-- 1. the customer picks up, talks 40 s, the agent hangs up
local log = run({ odoo_body = ALLOWED, bridge = { answer = true, ring = 8, talk = 40, cause = "NORMAL_CLEARING", agent_hangs_up = true } })
check("1 no error " .. tostring(log.error), not log.error)
check("1 Odoo asked for this call and this agent", log.asked.path == "/whatsapp/call/server/outbound"
      and log.asked.fields[1][2] == "42" and log.asked.fields[2][2] == "agent5")
local bridge = log.bridges[1] or ""
check("1 through the gateway of the number", bridge:find("]sofia/gateway/meta_1110001/+237670000000", 1, true) ~= nil)
check("1 Opus, SDES, ringing heard", bridge:find("absolute_codec_string=OPUS", 1, true) ~= nil
      and bridge:find("rtp_secure_media=mandatory:AES_CM_128_HMAC_SHA1_80", 1, true) ~= nil
      and bridge:find("ignore_early_media=false", 1, true) ~= nil and bridge:find("leg_timeout=45", 1, true) ~= nil)
check("1 the business number shown", bridge:find("origination_caller_id_number=+22890000001", 1, true) ~= nil)
check("1 answer told by the customer's leg", bridge:find("api_on_answer=luarun ocd_whatsapp_event.lua outbound_answered uuid-out agent5", 1, true) ~= nil)
local ended = log.events[#log.events]
check("1 completed, ended by the agent, 40 s", ended and ended.event == "ended" and ended.outcome == "completed"
      and ended.ended_by == "agent" and ended.talk == 40 and ended.call == "42")
check("1 the record of the call", log.vars.ocd_outcome == "completed" and log.vars.ocd_outbound == "1")

-- 2. no answer from the customer
log = run({ odoo_body = ALLOWED, bridge = { ring = 45, cause = "NO_ANSWER" } })
ended = log.events[#log.events]
check("2 missed, by the customer", ended.outcome == "missed" and ended.ended_by == "customer" and ended.talk == 0)
check("2 the agent's phone told", log.hangup == "NO_ANSWER")

-- 3. Odoo refuses (no permission, call not prepared)
log = run({ odoo_body = "error=The customer did not allow the calls\n" })
check("3 no call", #log.bridges == 0 and #log.events == 0)
check("3 refused with the reason", log.responds[1] == "403 The customer did not allow the calls")

-- 4. Odoo does not answer: no call (a call of the company is paid)
log = run({ odoo_code = 0, odoo_body = "" })
check("4 no call without Odoo", #log.bridges == 0 and log.responds[1] == "403 Odoo does not answer")

-- 5. the agent hangs up while it rings
log = run({ odoo_body = ALLOWED, bridge = { ring = 5, cause = "ORIGINATOR_CANCEL", agent_hangs_up = true } })
ended = log.events[#log.events]
check("5 missed, ended by the agent", ended.outcome == "missed" and ended.ended_by == "agent")

-- 6. Meta refuses the call (permission, limit): failed
log = run({ odoo_body = ALLOWED, bridge = { ring = 1, cause = "NORMAL_TEMPORARY_FAILURE" } })
ended = log.events[#log.events]
check("6 failed", ended.outcome == "failed" and ended.ended_by == "system" and ended.cause == "NORMAL_TEMPORARY_FAILURE")

-- 7. the customer hung up, Meta told Odoo first: the phone hung up with the reason "ended at
-- Meta" (Q.850 31) before the call server saw the end of Meta: ended by the customer
log = run({ odoo_body = ALLOWED, bridge = { answer = true, ring = 5, talk = 30, cause = "NORMAL_CLEARING",
                                            agent_hangs_up = true, agent_reason = 'Q.850;cause=31;text="ended at Meta"' } })
ended = log.events[#log.events]
check("7 completed, ended by the customer", ended.outcome == "completed" and ended.ended_by == "customer" and ended.talk == 30)

-- 8. the longest duration of a call of the company: the customer's leg ends after it
log = run({ odoo_body = ALLOWED_30, bridge = { answer = true, ring = 5, talk = 1800, cause = "ALLOTTED_TIMEOUT" } })
check("8 the customer's leg ends after 30 minutes",
      (log.bridges[1] or ""):find("execute_on_answer='sched_hangup +1800 ALLOTTED_TIMEOUT'", 1, true) ~= nil)
ended = log.events[#log.events]
check("8 completed, ended by the system", ended.outcome == "completed" and ended.ended_by == "system"
      and ended.cause == "ALLOTTED_TIMEOUT")
check("8 without a limit: no end set", (run({ odoo_body = ALLOWED, bridge = { answer = true, talk = 5 } }).bridges[1] or "")
      :find("sched_hangup", 1, true) == nil)

-- 9. recorded: the customer hears it when they pick up, the call recorded from then
log = run({ odoo_body = ALLOWED_30 .. "record=1\n", sounds = { enregistrement = "/sounds/enregistrement.wav" },
            bridge = { answer = true, ring = 5, talk = 60, cause = "NORMAL_CLEARING" } })
check("9 the customer is told when they pick up",
      (log.bridges[1] or ""):find("execute_on_answer_notice='playback /sounds/enregistrement.wav'", 1, true) ~= nil
      and (log.bridges[1] or ""):find("execute_on_answer='sched_hangup +1800 ALLOTTED_TIMEOUT'", 1, true) ~= nil)
check("9 recording started before the bridge", log.recording and log.recording.bridges == 0 and log.recording.uuid == "uuid-out")
check("9 facts for ocd-call-sync", log.recording_facts and log.recording_facts.values.call == "42")
log = run({ odoo_body = ALLOWED .. "record=1\n", bridge = { answer = true, talk = 5 } })
check("9 without the message: recorded all the same, the team warned",
      log.recording and (log.console or ""):find("no message enregistrement", 1, true) ~= nil
      and not (log.bridges[1] or ""):find("execute_on_answer_notice", 1, true))
check("9 not recorded unless Odoo asks", not run({ odoo_body = ALLOWED, bridge = { answer = true, talk = 5 } }).recording)

print(string.format("%d checks, %d failures", count, failures))
os.exit(failures == 0 and 0 or 1)
