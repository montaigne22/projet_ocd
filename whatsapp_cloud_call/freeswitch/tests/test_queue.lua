-- Tests of the decisions of the queue, with plain Lua (no FreeSWITCH):
--   lua5.3 whatsapp_cloud_call/freeswitch/tests/test_queue.lua
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

local function same(a, b)
  if #a ~= #b then
    return false
  end
  for i = 1, #a do
    if a[i] ~= b[i] then
      return false
    end
  end
  return true
end

-- values from Meta and Odoo
check("digits", queue.digits("+237 670-00") == "23767000")
check("safe removes shell characters", queue.safe("wacid.AB'; rm -rf /") == "wacid.ABrm-rf/")
check("safe name", queue.safe_name("Awa, [Ngono] {x}") == "Awa Ngono x")
check("split", same(queue.split("agent1,agent2, agent3"), { "agent1", "agent2", "agent3" }))
local lines = queue.parse_lines("call=12\nname=Awa Ngono\nfirst=\nagents=agent5,agent7\nmax_wait=120\nvoicemail=0\n")
check("parse lines", lines.call == "12" and lines.name == "Awa Ngono" and lines.first == "")
check("shell quote", queue.shell_quote("it's") == "'it'\\''s'")

-- route from Odoo, else the copied agents
local route = queue.route(lines, { agents = { "agent9" } }, {})
check("route from odoo", route.from_odoo and same(route.agents, { "agent5", "agent7" }))
check("route max wait", route.max_wait == 120 and route.voicemail == false)
local fallback = queue.route(nil, { agents = { "agent9", "agent10" } }, { max_wait = 90 })
check("route fallback", not fallback.from_odoo and same(fallback.agents, { "agent9", "agent10" }))
check("route fallback wait", fallback.max_wait == 90 and fallback.voicemail == true)

-- who rings
local registered = { agent5 = true, agent7 = true }
local function is_registered(agent) return registered[agent] == true end
local r = queue.route({ call = "1", agents = "agent5,agent7,agent8", first = "agent7" }, {}, {})
local agents, timeout, kind = queue.pick(r, { round = 1, now = 100 }, is_registered)
check("first round: the agent of the conversation", same(agents, { "agent7" }) and kind == "first")
check("first timeout", timeout == queue.FIRST_TIMEOUT)
agents, timeout, kind = queue.pick(r, { round = 2, now = 100 }, is_registered)
check("then every connected agent", same(agents, { "agent5", "agent7" }) and kind == "all")
check("round timeout", timeout == queue.ROUND_TIMEOUT)
registered.agent7 = nil
agents = queue.pick(r, { round = 1, now = 100 }, is_registered)
check("agent of the conversation not connected: the others", same(agents, { "agent5" }))
registered.agent7 = true
agents, _, kind = queue.pick(r, { round = 3, now = 110, reconnect_agent = "agent7", reconnect_since = 100 }, is_registered)
check("agent cut off gets the call back alone", same(agents, { "agent7" }) and kind == "reconnect")
agents, _, kind = queue.pick(r, { round = 4, now = 140, reconnect_agent = "agent7", reconnect_since = 100 }, is_registered)
check("after the window, everyone", kind == "all" and #agents == 2)
registered.agent7 = nil
agents, _, kind = queue.pick(r, { round = 3, now = 104, reconnect_agent = "agent7", reconnect_since = 100 }, is_registered)
check("agent cut off not back yet: waits a few seconds", #agents == 0 and kind == "reconnect")
agents, _, kind = queue.pick(r, { round = 4, now = 110, reconnect_agent = "agent7", reconnect_since = 100 }, is_registered)
check("agent cut off gone (page closed): the others at once", kind == "all" and agents[1] == "agent5")
registered.agent7 = true
registered = {}
agents = queue.pick(r, { round = 2, now = 100 }, is_registered)
check("nobody connected", #agents == 0)

-- dial string
local dial = queue.dial_string({ "agent5", "agent7" }, 20, {
  domain = "calls.example.com", a_uuid = "uuid-1", call = "12", name = "Awa, Ngono", number = "+237670000000",
})
check("dial string legs", select(2, dial:gsub("user/agent%d@calls%.example%.com", "")) == 2)
check("dial string answer hook", dial:find("api_on_answer=luarun ocd_whatsapp_event.lua answered uuid-1 agent5", 1, true) ~= nil)
check("dial string name without comma", dial:find("origination_caller_id_name=Awa Ngono,", 1, true) ~= nil)
check("dial string header", dial:find("sip_h_X-OCD-Call=12", 1, true) ~= nil)
check("dial string starts with globals", dial:sub(1, 26) == "{ignore_early_media=true}[")

-- after a bridge
check("customer hung up", queue.after_bridge({ customer_up = false, agent = "agent5", cause = "NORMAL_CLEARING" }) == "customer_gone")
check("agent hung up", queue.after_bridge({ customer_up = true, agent = "agent5", cause = "NORMAL_CLEARING" }) == "agent_ended")
check("agent cut off", queue.after_bridge({ customer_up = true, agent = "agent5", cause = "MEDIA_TIMEOUT" }) == "reconnect")
check("agent cut off without cause", queue.after_bridge({ customer_up = true, agent = "agent5" }) == "reconnect")
check("nobody answered", queue.after_bridge({ customer_up = true, agent = nil, cause = "NO_ANSWER" }) == "retry")
-- the phone hung up because the call ended at Meta (Odoo told it first): the customer is gone,
-- never a reconnection (the colleagues would ring for a customer who hung up)
check("ended at Meta, told to the phone first", queue.after_bridge({ customer_up = true, agent = "agent5", cause = "NORMAL_UNSPECIFIED" }) == "customer_gone")
check("outbound: answered, the phone hung up for Meta", select(2, queue.outbound_end({ answered = true, agent_up = false, agent_cause = "NORMAL_UNSPECIFIED" })) == "customer")
check("reason of the BYE: ended at Meta", queue.reason_cause('Q.850;cause=31;text="ended at Meta"') == "NORMAL_UNSPECIFIED")
check("reason of the BYE: other causes", queue.reason_cause('Q.850;cause=16;text="NORMAL_CLEARING"') == nil
      and queue.reason_cause(nil) == nil and queue.reason_cause('Q.850;cause=41;text="media lost"') == nil)
check("outbound: the longest duration reached", select(2, queue.outbound_end({ answered = true, agent_up = true, cause = "ALLOTTED_TIMEOUT" })) == "system")
check("outbound: answered, the agent hung up", select(2, queue.outbound_end({ answered = true, agent_up = false, agent_cause = "NORMAL_CLEARING" })) == "agent")

-- waiting
local w = { max_wait = 180, open = true }
check("still waiting", not queue.should_stop_waiting(w, { start = 0, now = 100, talk = 0 }))
check("waited enough", queue.should_stop_waiting(w, { start = 0, now = 180, talk = 0 }))
check("talk time not counted", not queue.should_stop_waiting(w, { start = 0, now = 300, talk = 200 }))
check("nobody connected for long", queue.should_stop_waiting(w, { start = 0, now = 40, nobody_since = 5 }))
check("closed", queue.should_stop_waiting({ max_wait = 180, open = false }, { start = 0, now = 1 }))
check("reconnect window keeps waiting", not queue.should_stop_waiting(w, {
  start = 0, now = 500, talk = 0, reconnect_agent = "agent5", reconnect_since = 490,
}))

-- an agent whose voice does not get through
local st = { reconnects = 1 }
check("cut off after a conversation: gets it back", queue.note_cut_off(st, "agent5", 120) and not queue.excluded(st, "agent5"))
st.reconnects = 2
check("first failed answer: gets it back", queue.note_cut_off(st, "agent5", 3))
st.reconnects = 3
check("second failed answer: not rung again", not queue.note_cut_off(st, "agent5", 2) and queue.excluded(st, "agent5"))
local everyone = queue.pick({ agents = { "agent5", "agent7" }, first = {} }, { round = 2, now = 0, failed = st.failed },
  function() return true end)
check("excluded agent left out of the round", #everyone == 1 and everyone[1] == "agent7")
check("too many reconnections: no more waiting alone", not queue.note_cut_off({ reconnects = 4 }, "agent9", 300))
check("unknown agent: no waiting alone", not queue.note_cut_off({ reconnects = 1 }, nil, 3))

print(string.format("%d checks, %d failures", count, failures))
os.exit(failures == 0 and 0 or 1)
