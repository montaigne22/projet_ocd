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
  }
  local chunk = assert(loadfile(here .. "/scripts/ocd_whatsapp_outbound.lua"))
  local ok, err = pcall(chunk)
  os.time = real_time
  log.error = not ok and err or nil
  log.vars = vars
  return log
end

local ALLOWED = "number=237670000000\nphone_number_id=1110001\nbusiness_number=22890000001\nsrtp=SDES\nmax_ring=45\n"

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

print(string.format("%d checks, %d failures", count, failures))
os.exit(failures == 0 and 0 or 1)
