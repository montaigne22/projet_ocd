from datetime import timedelta

# Configuration parameters of the call server (Settings > WhatsApp > Calls).
PARAM_HOST = "whatsapp_cloud_call.server_host"
PARAM_SIP_PORT = "whatsapp_cloud_call.server_sip_port"
PARAM_WSS_PORT = "whatsapp_cloud_call.server_wss_port"
PARAM_TOKEN = "whatsapp_cloud_call.server_token"
PARAM_TURN_SECRET = "whatsapp_cloud_call.turn_secret"

DEFAULT_SIP_PORT = 5061
DEFAULT_WSS_PORT = 7443

# The call server reports every 30 seconds: silent for this long, the managers are alerted.
SERVER_SILENCE = timedelta(minutes=5)
# A call seen by Meta and not by the call server for this long is lost (the call server sends
# its record of the call again for hours when Odoo does not answer: wait before alerting).
LOST_AFTER = timedelta(minutes=10)
# A call still ringing or answered after this long missed its end (call server stopped).
STALE_AFTER = timedelta(hours=4)
# The TURN credentials given to an agent are valid for this long.
TURN_VALIDITY = timedelta(hours=12)

# Meta: the number of customers who may receive a template in 24 hours must be 2,000 or more
# to enable the calls.
CALLING_MIN_TIERS = ("TIER_2K", "TIER_10K", "TIER_100K", "TIER_UNLIMITED")

# Hang-up causes of the agent's leg that mean "the agent hung up" (else the agent was cut off).
NORMAL_CAUSES = ("NORMAL_CLEARING",)

# Prefix of the SIP users of the agents on the call server: agent<user id>.
AGENT_PREFIX = "agent"

MAX_VOICEMAIL_SIZE = 20 * 1024 * 1024
