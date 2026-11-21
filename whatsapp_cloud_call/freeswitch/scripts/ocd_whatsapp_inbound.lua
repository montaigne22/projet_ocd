-- A customer calls on WhatsApp (INVITE of Meta on the profile ocd_whatsapp): the queue.
--
-- Music while the free agents ring together (the agent of the conversation first); the first
-- who answers takes the call. An agent cut off (network, closed page) gets the call back while
-- the customer hears "we reconnect you". Nobody after the waiting time, or nobody connected:
-- the voicemail, sent to Odoo (kept in the spool and sent again by ocd-call-sync when Odoo does
-- not answer). Odoo is asked who rings; without its answer, all the connected agents ring.
package.path = "/usr/share/freeswitch/scripts/?.lua;" .. package.path

local queue = require("ocd.queue")
local odoo = require("ocd.odoo")

local api = freeswitch.API()
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

local function file_exists(path)
  local handle = io.open(path, "rb")
  if handle then
    handle:close()
    return true
  end
  return false
end

-- A prompt of the team (sounds/ocd/<name>.wav), else a short tone.
local function play(name)
  if not session:ready() then
    return
  end
  local path = settings.sounds .. "/" .. name .. ".wav"
  if file_exists(path) then
    session:execute("playback", path)
  else
    session:execute("playback", "tone_stream://%(250,100,800);loops=2")
  end
end

-- Music for a few seconds (stopped by uuid_break).
local function music(seconds)
  if not session:ready() then
    return
  end
  api:executeString("sched_api +" .. seconds .. " none uuid_break " .. uuid .. " all")
  session:execute("playback", settings.hold_music)
end

local function is_registered(agent)
  local contact = api:execute("sofia_contact", "ocd_agents/" .. queue.safe(agent, 32) .. "@" .. settings.domain) or ""
  return contact ~= "" and not contact:find("error/", 1, true)
end

session:setAutoHangup(false)

-- the customer: their number, or only their WhatsApp user ID (BSUID) when they hide their
-- number behind a WhatsApp username (in the From of Meta and the header x-wa-meta-user-id)
local from_user = var("sip_from_user") or var("caller_id_number") or ""
local call = {
  uuid = uuid,
  wacid = queue.safe(var("sip_h_x-wa-meta-wacid") or var("sip_h_X-WA-Meta-WACID") or var("sip_call_id")),
  number = from_user:match("^%+?%d+$") and queue.digits(from_user) or "",
  user_ref = queue.safe(var("sip_h_x-wa-meta-user-id") or var("sip_h_X-WA-Meta-User-ID") or "", 64),
  pnid = queue.safe(var("sip_h_x-wa-meta-phone-number-id") or var("sip_h_X-WA-Meta-Phone-Number-ID") or ""),
  business = queue.digits(var("sip_to_user") or var("destination_number")),
}
if call.number == "" and call.user_ref == "" then
  call.user_ref = queue.safe(from_user, 64)
end
local trunk = settings.trunks[call.pnid] or {}
setvar("ocd_wacid", call.wacid)
setvar("ocd_from", call.number)
setvar("ocd_user_ref", call.user_ref)
setvar("ocd_pnid", call.pnid)
setvar("ocd_outcome", "missed")
setvar("ocd_ended_by", "customer")
setvar("ocd_reconnects", 0)
setvar("ocd_talk", 0)
setvar("hangup_after_bridge", "false")
setvar("continue_on_fail", "true")
setvar("ringback", settings.hold_music)
setvar("transfer_ringback", settings.hold_music)
setvar("hold_music", settings.hold_music)

-- what Meta sent, in one line of the log (the first calls with Meta are checked with it)
log("NOTICE", "call of " .. (call.number ~= "" and "+" .. call.number or "user " .. call.user_ref) ..
    " to +" .. call.business .. ", phone number id " .. call.pnid .. ", wacid " .. call.wacid ..
    ", from " .. (var("sip_network_ip") or "?") .. ", signed as " .. (var("sip_auth_username") or "nobody"))
session:answer()
log("NOTICE", "answered: codec " .. (var("rtp_use_codec_name") or "?") .. ", SRTP " ..
    (var("rtp_has_crypto") or "none"))
if not session:ready() then
  return
end

local route = queue.route(odoo.route(settings, call), settings, trunk)
if route.call ~= "" then
  setvar("ocd_call", route.call)
end
if not route.from_odoo then
  log("WARNING", "Odoo did not answer: all the connected agents ring")
end
play("accueil")

local state = {
  start = os.time(),
  talk = 0,
  round = 0,
  reconnects = 0,
  now = os.time(),
}
local answered_agent = nil
local last_route = os.time()
local outcome = "missed"
local ended_by = "customer"

while session:ready() do
  state.now = os.time()
  if state.now - last_route >= 10 and state.round > 0 then
    -- agents freed or connected since: ask Odoo again (the previous answer otherwise)
    local fresh = odoo.route(settings, call)
    if fresh then
      route = queue.route(fresh, settings, trunk)
      if route.call ~= "" then
        setvar("ocd_call", route.call)
      end
    end
    last_route = state.now
  end
  if queue.should_stop_waiting(route, state) then
    break
  end
  state.round = state.round + 1
  local agents, timeout, kind = queue.pick(route, state, is_registered)
  if #agents == 0 then
    state.nobody_since = state.nobody_since or state.now
    music(5)
  else
    state.nobody_since = nil
    setvar("ocd_round_agent", "")
    setvar("originate_disposition", "")
    local started = os.time()
    session:execute("bridge", queue.dial_string(agents, timeout, {
      domain = settings.domain, a_uuid = uuid, call = route.call, name = route.name,
      number = call.number,
    }))
    local round_agent = var("ocd_round_agent")
    if not round_agent and var("originate_disposition") == "SUCCESS" then
      -- answered and ended before the hook of the agent's leg noted who answered
      round_agent = "unknown"
    end
    if round_agent then
      answered_agent = round_agent ~= "unknown" and round_agent or answered_agent
      local answered_at = tonumber(var("ocd_answer_epoch") or "") or started
      state.talk = state.talk + math.max(0, os.time() - answered_at)
      setvar("ocd_talk", state.talk)
      if answered_agent then
        setvar("ocd_answered_agent", answered_agent)
      end
    end
    local action = queue.after_bridge({
      customer_up = session:ready(),
      agent = round_agent,
      cause = var("last_bridge_hangup_cause") or var("bridge_hangup_cause"),
    })
    if action == "customer_gone" then
      outcome = (answered_agent or round_agent) and "completed" or "missed"
      ended_by = "customer"
      break
    elseif action == "agent_ended" then
      outcome = "completed"
      ended_by = "agent"
      break
    elseif action == "reconnect" then
      state.reconnects = state.reconnects + 1
      local agent = round_agent ~= "unknown" and round_agent or nil
      local round_talk = math.max(0, os.time() - (tonumber(var("ocd_answer_epoch") or "") or started))
      local cause = tostring(var("last_bridge_hangup_cause"))
      if queue.note_cut_off(state, agent, round_talk) then
        state.reconnect_agent = agent
        state.reconnect_since = os.time()
        if cause == "NETWORK_OUT_OF_ORDER" then
          -- ended by the watch: the agent is gone already, the colleagues ring at once (the
          -- agent still gets it back if they connect again in the meantime)
          state.reconnect_since = os.time() - queue.RECONNECT_GRACE
        end
        log("NOTICE", "agent " .. round_agent .. " cut off (" .. cause .. ") after " .. round_talk .. " s")
      else
        -- the voice of this agent does not get through: the colleagues, else the voicemail
        state.reconnect_agent = nil
        log("WARNING", "agent " .. round_agent .. " cut off again (" .. cause .. ") after " .. round_talk ..
            " s: not rung again for this call")
      end
      setvar("ocd_reconnects", state.reconnects)
      odoo.event(settings, { event = "agent_lost", call = route.call, wacid = call.wacid, uuid = uuid,
                             agent = round_agent })
      play("reconnexion")
    else
      if kind == "reconnect" and state.reconnect_agent and os.time() - (state.reconnect_since or 0) >= queue.RECONNECT_WINDOW then
        state.reconnect_agent = nil
      end
      local disposition = var("originate_disposition") or ""
      if disposition == "INCOMPATIBLE_DESTINATION" and #agents == 1 then
        -- the agent answered, but their phone gave no network address the call server can reach
        -- (STUN/TURN not reached): counted as an answer that failed
        queue.note_cut_off(state, agents[1], 0)
        log("WARNING", "agent " .. agents[1] .. " answered, but their phone gave no usable network address" ..
            " (STUN/TURN of the call server not reached)" ..
            (queue.excluded(state, agents[1]) and ": not rung again for this call" or ""))
      end
      if os.time() - started < 3 then
        -- refused at once (busy, declined, not connected): music before ringing again
        log("DEBUG", "agents did not ring: " .. disposition)
        music(5)
      end
    end
  end
end

-- the time the customer waited for an agent (the voicemail after it is not counted)
local waited = os.time() - state.start - state.talk

-- the customer waited without an agent: the voicemail (or a message to call back)
if session:ready() and outcome == "missed" then
  if route.voicemail then
    play("messagerie")
    session:execute("playback", "tone_stream://%(500,0,800)")
    local dir = settings.spool .. "/voicemail"
    local path = dir .. "/" .. uuid .. ".wav"
    session:execute("set", "record_sample_rate=16000")
    session:recordFile(path, 120, 200, 5)
    local handle = io.open(path, "rb")
    local size = handle and handle:seek("end") or 0
    if handle then
      handle:close()
    end
    if size > 16000 then
      outcome = "voicemail"
      -- the facts of the call next to the file, for ocd-call-sync if Odoo does not answer now
      local facts = io.open(dir .. "/" .. uuid .. ".txt", "w")
      if facts then
        facts:write("call=" .. route.call .. "\nwacid=" .. call.wacid .. "\nuuid=" .. uuid ..
                    "\nnumber=" .. call.number .. "\nuser_ref=" .. call.user_ref ..
                    "\nphone_number_id=" .. call.pnid .. "\n")
        facts:close()
      end
      if odoo.voicemail(settings, path, { call = route.call, wacid = call.wacid, uuid = uuid,
                                          number = call.number, user_ref = call.user_ref,
                                          phone_number_id = call.pnid }) then
        os.remove(path)
        os.remove(dir .. "/" .. uuid .. ".txt")
      end
    else
      os.remove(path)
    end
  else
    play("indisponible")
  end
  ended_by = "system"
end

local cause = var("last_bridge_hangup_cause") or var("hangup_cause")
log("NOTICE", "end: " .. outcome .. ", ended by " .. ended_by .. ", cause " .. (cause or "none") ..
    (session:ready() and ", hang-up sent to Meta" or ", the customer hung up"))
setvar("ocd_outcome", outcome)
setvar("ocd_ended_by", ended_by)
setvar("ocd_wait", waited)
-- the customer is let go first (Meta told at once), Odoo after (up to 3 seconds)
if session:ready() then
  session:hangup("NORMAL_CLEARING")
end
odoo.event(settings, {
  event = "ended", call = route.call, wacid = call.wacid, uuid = uuid, agent = answered_agent,
  outcome = outcome, ended_by = ended_by, wait = waited, talk = state.talk,
  reconnects = state.reconnects, cause = cause,
  number = call.number, user_ref = call.user_ref, phone_number_id = call.pnid,
})
