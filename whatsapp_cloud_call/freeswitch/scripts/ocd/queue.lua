-- Decisions of the queue of the WhatsApp calls, without FreeSWITCH: who rings, what to do
-- after a ring or a conversation with an agent. Tested with plain Lua (tests/test_queue.lua).
local M = {}

-- How long an agent cut off during a call gets it back alone, before the others ring too; when
-- they are not connected again after the grace (page closed), the others ring at once.
M.RECONNECT_WINDOW = 30
M.RECONNECT_GRACE = 8
-- Ring time of a round: the agent of the conversation alone, then every free agent.
M.FIRST_TIMEOUT = 15
M.ROUND_TIMEOUT = 20
-- Nobody connected for this long: the voicemail without waiting the whole time.
M.NOBODY_LIMIT = 30
-- Hang-up causes of the agent's leg meaning "the agent hung up"; any other one means the agent
-- was cut off (network, closed page, media timeout), and the customer waits for them.
M.NORMAL_CAUSES = { NORMAL_CLEARING = true }
-- An agent whose voice does not get through (their leg cut off this soon after they answered)
-- twice in a call is not rung again for it: the colleagues ring, else the voicemail. Never an
-- endless loop of rings for an agent who answers but cannot talk (network, relay).
M.FAILED_ANSWER_SECONDS = 15
M.MAX_FAILED_ANSWERS = 2
-- Cut off more often in a call: no more waiting for that agent alone.
M.MAX_RECONNECTS = 3

-- Whether the agent is no longer rung for this call.
function M.excluded(state, agent)
  return ((state.failed or {})[agent] or 0) >= M.MAX_FAILED_ANSWERS
end

-- An agent cut off after <talk> seconds: noted; true when they still get the call back alone.
-- state: reconnects (this one counted), failed
function M.note_cut_off(state, agent, talk)
  if not agent then
    return false
  end
  state.failed = state.failed or {}
  if (talk or 0) < M.FAILED_ANSWER_SECONDS then
    state.failed[agent] = (state.failed[agent] or 0) + 1
  end
  return not M.excluded(state, agent) and (state.reconnects or 0) <= M.MAX_RECONNECTS
end

function M.digits(value)
  return (tostring(value or ""):gsub("%D", ""))
end

-- A value from Meta or from Odoo that goes to a shell command or a dial string.
function M.safe(value, size)
  local text = tostring(value or ""):gsub("[^%w%._%-:=+/@]", "")
  return text:sub(1, size or 128)
end

-- A name shown on the phone of the agents: no character that breaks a dial string.
function M.safe_name(value)
  local text = tostring(value or ""):gsub("[%[%]{}<>,'\"\\=^]", " "):gsub("%s+", " ")
  text = text:gsub("^%s+", ""):gsub("%s+$", "")
  return text:sub(1, 60)
end

function M.split(value)
  local items = {}
  for item in tostring(value or ""):gmatch("[^,%s]+") do
    items[#items + 1] = item
  end
  return items
end

-- Answer of Odoo: lines "key=value".
function M.parse_lines(text)
  local values = {}
  for line in tostring(text or ""):gmatch("[^\r\n]+") do
    local key, value = line:match("^([%w_]+)=(.*)$")
    if key then
      values[key] = value
    end
  end
  return values
end

-- The route of a call: what Odoo answered, else the agents copied on the call server.
function M.route(answer, settings, trunk)
  trunk = trunk or {}
  local route = {
    from_odoo = false,
    call = "",
    name = "",
    first = {},
    agents = {},
    max_wait = tonumber(trunk.max_wait) or 180,
    voicemail = trunk.voicemail ~= false,
    open = true,
  }
  if answer and answer.agents then
    route.from_odoo = true
    route.call = M.safe(answer.call, 16)
    route.name = M.safe_name(answer.name)
    route.first = M.split(answer.first)
    route.agents = M.split(answer.agents)
    route.max_wait = tonumber(answer.max_wait) or route.max_wait
    route.voicemail = answer.voicemail ~= "0"
    route.open = answer.open ~= "0"
  else
    for _, agent in ipairs((settings or {}).agents or {}) do
      route.agents[#route.agents + 1] = agent
    end
  end
  return route
end

local function contains(list, value)
  for _, item in ipairs(list) do
    if item == value then
      return true
    end
  end
  return false
end

-- Who rings this round: {agents, timeout}; no agent when nobody is connected.
-- state: round, reconnect_agent, reconnect_since, now
function M.pick(route, state, is_registered)
  local function registered(list)
    local result = {}
    for _, agent in ipairs(list) do
      if not M.excluded(state, agent) and is_registered(agent) and not contains(result, agent) then
        result[#result + 1] = agent
      end
    end
    return result
  end
  local since = state.now - (state.reconnect_since or 0)
  if state.reconnect_agent and since < M.RECONNECT_WINDOW then
    -- the agent cut off reconnects: they get the call back alone for a while
    local back = registered({ state.reconnect_agent })
    if #back > 0 or since < M.RECONNECT_GRACE then
      return back, M.FIRST_TIMEOUT, "reconnect"
    end
  end
  if state.round == 1 and #route.first > 0 then
    local first = registered(route.first)
    if #first > 0 then
      return first, M.FIRST_TIMEOUT, "first"
    end
  end
  local everyone = registered(route.agents)
  if state.reconnect_agent and not M.excluded(state, state.reconnect_agent)
      and is_registered(state.reconnect_agent) and not contains(everyone, state.reconnect_agent) then
    table.insert(everyone, 1, state.reconnect_agent)
  end
  return everyone, M.ROUND_TIMEOUT, "all"
end

-- Dial string ringing the agents together; the first who answers takes the call.
-- opts: domain, profile, a_uuid, call, name, number, script
function M.dial_string(agents, timeout, opts)
  local legs = {}
  for _, agent in ipairs(agents) do
    local vars = {
      "leg_timeout=" .. tostring(timeout),
      "media_timeout=10000",
      "ocd_agent=" .. M.safe(agent, 32),
      "sip_h_X-OCD-Call=" .. M.safe(opts.call, 16),
      "origination_caller_id_name=" .. M.safe_name(opts.name),
      "origination_caller_id_number=" .. M.digits(opts.number),
      "api_on_answer=luarun " .. (opts.script or "ocd_whatsapp_event.lua") .. " answered "
        .. M.safe(opts.a_uuid, 64) .. " " .. M.safe(agent, 32),
    }
    legs[#legs + 1] = "[" .. table.concat(vars, ",") .. "]user/" .. M.safe(agent, 32) .. "@" .. M.safe(opts.domain, 128)
  end
  return "{ignore_early_media=true}" .. table.concat(legs, ",")
end

-- After a bridge: what to do.
-- info: customer_up, agent (who answered this round, or nil), cause (hang-up cause of the agent)
-- Returns "customer_gone", "agent_ended", "reconnect" or "retry".
function M.after_bridge(info)
  if not info.customer_up then
    return "customer_gone"
  end
  if info.agent and info.agent ~= "" then
    if M.NORMAL_CAUSES[info.cause or ""] then
      return "agent_ended"
    end
    return "reconnect"
  end
  return "retry"
end

-- Whether the customer waited long enough for the voicemail.
-- state: start, talk, now, nobody_since (nil while an agent is connected), reconnect_agent, reconnect_since
function M.should_stop_waiting(route, state)
  if not route.open then
    return true
  end
  if state.reconnect_agent and state.now - (state.reconnect_since or 0) < M.RECONNECT_WINDOW then
    return false
  end
  local waited = state.now - state.start - (state.talk or 0)
  if waited >= route.max_wait then
    return true
  end
  if state.nobody_since and state.now - state.nobody_since >= M.NOBODY_LIMIT then
    return true
  end
  return false
end

-- A shell argument, quoted.
function M.shell_quote(value)
  return "'" .. tostring(value):gsub("'", "'\\''") .. "'"
end

return M
