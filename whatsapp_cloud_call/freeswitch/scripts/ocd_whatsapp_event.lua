-- An agent answered (api_on_answer of the agent's leg): noted on the customer's leg, told to
-- Odoo, then watched. Run by luarun, in its own thread: the call never waits for Odoo.
--   luarun ocd_whatsapp_event.lua answered <uuid of the customer's leg> <agent>
--
-- The watch: an agent whose page closed or whose network fell is no longer connected to the call
-- server, but their leg can stay up without voice for long (FreeSWITCH does not always notice
-- it, through a TURN relay in particular). Not connected for 9 seconds: their leg is ended as
-- "network out of order", the queue gives the call to the colleagues at once while the customer
-- waits.
package.path = "/usr/share/freeswitch/scripts/?.lua;" .. package.path

local queue = require("ocd.queue")
local odoo = require("ocd.odoo")

local WATCH_EVERY_MS = 3000
local GONE_CHECKS = 3

local event = queue.safe(argv[1], 32)
local a_uuid = queue.safe(argv[2], 64)
local agent = queue.safe(argv[3], 32)
local api = freeswitch.API()

local function get(uuid, name)
  local value = api:execute("uuid_getvar", uuid .. " " .. name) or ""
  if value == "_undef_" or value:find("^%-ERR") then
    return ""
  end
  return value
end

-- the agent's leg bridged with the customer's leg (show calls: uuid,...,b_uuid,...)
local function agent_leg()
  local lines = api:execute("show", "calls as delim |") or ""
  local header
  for line in lines:gmatch("[^\n]+") do
    local fields = {}
    for field in (line .. "|"):gmatch("([^|]*)|") do
      fields[#fields + 1] = field
    end
    if not header then
      header = {}
      for index, name in ipairs(fields) do
        header[name] = index
      end
    elseif header.uuid and header.b_uuid then
      if fields[header.uuid] == a_uuid then
        return fields[header.b_uuid]
      elseif fields[header.b_uuid] == a_uuid then
        return fields[header.uuid]
      end
    end
  end
  return nil
end

if event == "answered" and a_uuid ~= "" and agent ~= "" then
  api:execute("uuid_setvar", a_uuid .. " ocd_round_agent " .. agent)
  api:execute("uuid_setvar", a_uuid .. " ocd_answer_epoch " .. tostring(os.time()))
  local settings = odoo.load_settings()
  local start = tonumber(get(a_uuid, "start_epoch")) or os.time()
  local talk = tonumber(get(a_uuid, "ocd_talk")) or 0
  odoo.event(settings, {
    event = "answered", call = get(a_uuid, "ocd_call"), wacid = get(a_uuid, "ocd_wacid"), uuid = a_uuid,
    agent = agent, wait = math.max(0, os.time() - start - talk),
  })

  -- the watch, as long as the agent talks with the customer
  local gone = 0
  local leg = nil
  for _ = 1, 3 do
    freeswitch.msleep(1000)
    leg = agent_leg()
    if leg then
      break
    end
  end
  while leg and api:execute("uuid_exists", leg) == "true" do
    freeswitch.msleep(WATCH_EVERY_MS)
    if api:execute("uuid_exists", leg) ~= "true" or agent_leg() ~= leg then
      break
    end
    local contact = api:execute("sofia_contact", "ocd_agents/" .. agent .. "@" .. settings.domain) or ""
    if contact == "" or contact:find("error/", 1, true) then
      gone = gone + 1
    else
      gone = 0
    end
    if gone >= GONE_CHECKS then
      freeswitch.consoleLog("NOTICE", "[ocd] " .. a_uuid .. " agent " .. agent .. " no longer connected: leg ended\n")
      api:execute("uuid_kill", leg .. " NETWORK_OUT_OF_ORDER")
      break
    end
  end
end
