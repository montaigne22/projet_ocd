-- Exchanges of the call server with Odoo (curl, a few seconds at most: a call never waits for
-- Odoo; without an answer, the queue uses the agents copied on the call server).
local queue = require("ocd.queue")

local M = {}

M.SETTINGS_FILE = "/var/lib/freeswitch/ocd/settings.lua"

-- The settings written by ocd-call-sync (every 30 seconds); defaults when missing.
function M.load_settings(path)
  local settings = {
    odoo_url = "",
    headers_file = "/var/lib/freeswitch/ocd/odoo_headers",
    domain = "",
    spool = "/var/spool/ocd-calls",
    sounds = "/usr/share/freeswitch/sounds/ocd",
    -- the messages of sounds/ made ready at the start (WAV, and MP3 decoded): docker/entrypoint.sh
    sounds_ready = "/var/lib/freeswitch/sounds-ocd",
    -- the messages of each number given in Odoo (ocd-call-sync): sounds_odoo/<phone number ID>/
    sounds_odoo = "/var/lib/freeswitch/ocd/sounds",
    hold_music = "local_stream://moh",
    agents = {},
    trunks = {},
  }
  local chunk = loadfile(path or M.SETTINGS_FILE)
  if chunk then
    local ok, loaded = pcall(chunk)
    if ok and type(loaded) == "table" then
      for key, value in pairs(loaded) do
        settings[key] = value
      end
    end
  end
  return settings
end

-- POST to Odoo; returns (http code, body). fields: {{key, value}, ...}
function M.post(settings, path, fields, timeout, file)
  if not settings.odoo_url or settings.odoo_url == "" then
    return 0, ""
  end
  local args = {
    "curl", "-sS", "--max-time", tostring(timeout or 2), "--connect-timeout", "2",
    "-A", "ocd-call-server", "-H", "@" .. settings.headers_file,
  }
  for _, field in ipairs(fields or {}) do
    if file then
      args[#args + 1] = "--form-string"
    else
      args[#args + 1] = "--data-urlencode"
    end
    args[#args + 1] = field[1] .. "=" .. tostring(field[2] or "")
  end
  if file then
    args[#args + 1] = "-F"
    args[#args + 1] = "file=@" .. file .. ";type=audio/wav"
  end
  args[#args + 1] = "-w"
  args[#args + 1] = "\n%{http_code}"
  args[#args + 1] = settings.odoo_url .. path
  local quoted = {}
  for index, arg in ipairs(args) do
    quoted[index] = queue.shell_quote(arg)
  end
  local pipe = io.popen(table.concat(quoted, " ") .. " 2>/dev/null")
  if not pipe then
    return 0, ""
  end
  local output = pipe:read("*a") or ""
  pipe:close()
  local body, code = output:match("^(.*)\n(%d%d%d)$")
  return tonumber(code) or 0, body or ""
end

-- A recorded message (<name>.wav): the one of the number called given in Odoo (fetched by
-- ocd-call-sync), else the one of the team made ready at the start (Docker: WAV or MP3 of
-- sounds/), else in the folder of the sounds itself (installation without Docker); nil if none.
function M.sound(settings, name, number_id)
  local dirs = {}
  local number = tostring(number_id or ""):gsub("[^%w]", "")
  if number ~= "" and (settings.sounds_odoo or "") ~= "" then
    dirs[#dirs + 1] = settings.sounds_odoo .. "/" .. number
  end
  dirs[#dirs + 1] = settings.sounds_ready or ""
  dirs[#dirs + 1] = settings.sounds or ""
  for _, dir in ipairs(dirs) do
    if dir ~= "" then
      local path = dir .. "/" .. name .. ".wav"
      local handle = io.open(path, "rb")
      if handle then
        handle:close()
        return path
      end
    end
  end
  return nil
end

-- The recording of the call (asked by Odoo): from the moment the customer and an agent are put
-- together (not the waiting) to the end, mixed, 16 kHz, in spool/recordings/<uuid>.wav; sent to
-- Odoo by ocd-call-sync once the call ended (in MP3).
function M.recording_start(session, settings, uuid)
  local path = settings.spool .. "/recordings/" .. uuid .. ".wav"
  session:setVariable("RECORD_BRIDGE_REQ", "true")
  session:setVariable("RECORD_STEREO", "false")
  session:setVariable("record_sample_rate", "16000")
  session:execute("record_session", path)
  return path
end

-- The facts of a recording for ocd-call-sync (the call in Odoo), written once the call ended.
function M.recording_facts(path, values)
  local handle = io.open((path:gsub("%.wav$", ".txt")), "w")
  if not handle then
    return false
  end
  for _, key in ipairs({ "call", "wacid", "uuid" }) do
    if values[key] and values[key] ~= "" then
      handle:write(key .. "=" .. tostring(values[key]) .. "\n")
    end
  end
  handle:close()
  return true
end

function M.route(settings, call)
  local code, body = M.post(settings, "/whatsapp/call/server/route", {
    { "wacid", call.wacid }, { "uuid", call.uuid }, { "number", call.number },
    { "user_ref", call.user_ref }, { "phone_number_id", call.pnid }, { "business_number", call.business },
  }, 2)
  if code ~= 200 then
    return nil
  end
  return queue.parse_lines(body)
end

function M.event(settings, values)
  local fields = {}
  for _, key in ipairs({ "event", "call", "wacid", "uuid", "agent", "outcome", "ended_by", "wait",
                         "talk", "reconnects", "cause", "number", "user_ref", "phone_number_id" }) do
    if values[key] ~= nil then
      fields[#fields + 1] = { key, values[key] }
    end
  end
  local code = M.post(settings, "/whatsapp/call/server/event", fields, 3)
  return code == 200
end

function M.voicemail(settings, path, values)
  local fields = {}
  for _, key in ipairs({ "call", "wacid", "uuid", "number", "user_ref", "phone_number_id" }) do
    fields[#fields + 1] = { key, values[key] or "" }
  end
  local code = M.post(settings, "/whatsapp/call/server/voicemail", fields, 20, path)
  return code == 200
end

return M
