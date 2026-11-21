-- Test only: the customer of the fake Meta. Records what the call server sends
-- (/tmp/meta/<name>.wav, what the customer hears), sends a steady tone (440 Hz, easy to measure
-- on the other side), hangs up after <seconds>.
--   originate {meta_name=<name>,meta_seconds=<seconds>,...}sofia/gateway/ocd/+22890000001 &lua(/opt/fake_meta/meta_call.lua)
-- (originate splits its application on spaces: the values come as variables of the channel)
local name = tostring(session:getVariable("meta_name") or "call"):gsub("[^%w_%-%.]", "")
local seconds = tonumber(session:getVariable("meta_seconds") or "60") or 60
local api = freeswitch.API()
session:setVariable("RECORD_READ_ONLY", "true")
-- the tone paced by a timer (else written as fast as possible on this outbound leg)
session:setVariable("timer_name", "soft")
session:execute("record_session", "/tmp/meta/" .. name .. ".wav")
api:executeString("sched_api +" .. seconds .. " none uuid_kill " .. session:get_uuid())
while session:ready() do
  -- (a pause of 0 ms plays nothing: 10 ms)
  session:execute("playback", "tone_stream://%(5000,10,440)")
end
