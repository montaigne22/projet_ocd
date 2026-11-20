-- An agent answered (api_on_answer of the agent's leg): noted on the customer's leg, told to
-- Odoo. Run by luarun, in its own thread: the call never waits for Odoo.
--   luarun ocd_whatsapp_event.lua answered <uuid of the customer's leg> <agent>
package.path = "/usr/share/freeswitch/scripts/?.lua;" .. package.path

local queue = require("ocd.queue")
local odoo = require("ocd.odoo")

local event = queue.safe(argv[1], 32)
local a_uuid = queue.safe(argv[2], 64)
local agent = queue.safe(argv[3], 32)
local api = freeswitch.API()

if event == "answered" and a_uuid ~= "" and agent ~= "" then
  api:execute("uuid_setvar", a_uuid .. " ocd_round_agent " .. agent)
  api:execute("uuid_setvar", a_uuid .. " ocd_answer_epoch " .. tostring(os.time()))
  local function get(name)
    local value = api:execute("uuid_getvar", a_uuid .. " " .. name) or ""
    if value == "_undef_" or value:find("^%-ERR") then
      return ""
    end
    return value
  end
  local settings = odoo.load_settings()
  local start = tonumber(get("start_epoch")) or os.time()
  local talk = tonumber(get("ocd_talk")) or 0
  odoo.event(settings, {
    event = "answered", call = get("ocd_call"), wacid = get("ocd_wacid"), uuid = a_uuid,
    agent = agent, wait = math.max(0, os.time() - start - talk),
  })
end
