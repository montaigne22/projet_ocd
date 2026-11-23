from datetime import timedelta

# Configuration parameters of the call server (Settings > WhatsApp > Calls).
PARAM_HOST = "whatsapp_cloud_call.server_host"
PARAM_SIP_PORT = "whatsapp_cloud_call.server_sip_port"
PARAM_WSS_PORT = "whatsapp_cloud_call.server_wss_port"
PARAM_TOKEN = "whatsapp_cloud_call.server_token"
PARAM_TURN_SECRET = "whatsapp_cloud_call.turn_secret"
PARAM_TURN_TLS_PORT = "whatsapp_cloud_call.turn_tls_port"

DEFAULT_SIP_PORT = 5061
DEFAULT_WSS_PORT = 7443
# TURN over TLS: 443 passes almost every firewall; 5349 when nginx holds 443 on the machine
DEFAULT_TURN_TLS_PORT = 443

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

# Calls of the company (phase 2): the call server takes a call prepared by Odoo for this long
# after the click of the agent; WhatsApp rings the customer this long at most.
OUTBOUND_PREPARED_FOR = timedelta(minutes=2)
OUTBOUND_MAX_RING = 45
# A call of the company noted by Meta is linked to the call prepared in Odoo within this time.
OUTBOUND_META_LINK = timedelta(minutes=15)

# The thresholds to open the calls to all the customers (docs/APPELS_WHATSAPP.md), measured on
# the last days: calls cut under 2 %, voicemail while an agent was free under 5 %, average wait
# under 1 minute during the call hours.
CALL_STATS_DAYS = 14
CALL_MAX_CUT_RATE = 0.02
CALL_MAX_VOICEMAIL_RATE = 0.05
CALL_MAX_AVERAGE_WAIT = 60

# Cost of the calls of the company (phase 2.5): Meta bills them by pulses of 6 seconds (a pulse
# begun is due), at the rate of the country called; the calls of the customers are free.
CALL_PULSE_SECONDS = 6
# A call of the company is cut after this long (minutes; 0: no limit), by the call server.
DEFAULT_OUTBOUND_MAX_MINUTES = 30
# Countries where Meta refuses the calls of a company (November 2026): calling code -> name.
CALL_BLOCKED_PREFIXES = {
    "1": "United States / Canada",
    "20": "Egypt",
    "84": "Vietnam",
    "234": "Nigeria",
}

# Recordings of the calls (phase 3.1): sent by the call server in MP3 (WAV when it could not
# convert it); kept this many days by default, then deleted (0: kept).
MAX_RECORDING_SIZE = 100 * 1024 * 1024
DEFAULT_RECORDING_DAYS = 90
