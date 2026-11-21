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

function M.route(settings, call)
  local code, body = M.post(settings, "/whatsapp/call/server/route", {
    { "wacid", call.wacid }, { "uuid", call.uuid }, { "number", call.number },
    { "phone_number_id", call.pnid }, { "business_number", call.business },
  }, 2)
  if code ~= 200 then
    return nil
  end
  return queue.parse_lines(body)
end

function M.event(settings, values)
  local fields = {}
  for _, key in ipairs({ "event", "call", "wacid", "uuid", "agent", "outcome", "ended_by", "wait",
                         "talk", "reconnects", "cause", "number", "phone_number_id" }) do
    if values[key] ~= nil then
      fields[#fields + 1] = { key, values[key] }
    end
  end
  local code = M.post(settings, "/whatsapp/call/server/event", fields, 3)
  return code == 200
end

function M.voicemail(settings, path, values)
  local fields = {}
  for _, key in ipairs({ "call", "wacid", "uuid", "number", "phone_number_id" }) do
    fields[#fields + 1] = { key, values[key] or "" }
  end
  local code = M.post(settings, "/whatsapp/call/server/voicemail", fields, 20, path)
  return code == 200
end

return M
