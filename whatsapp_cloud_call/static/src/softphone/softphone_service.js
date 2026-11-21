import { proxy } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

const JSSIP_URL = "/whatsapp_cloud_call/static/lib/jssip/jssip.min.js";
// The voice of an agent lost for this long (network): the call is left, the call server gives
// it back to them (or to a colleague) while the customer waits.
const MEDIA_LOST_MS = 6000;

/**
 * The phone of the agents: connected to the call server (SIP over WSS, JsSIP) while the agent
 * takes the calls; rings, answers, mutes, hangs up. The state is plain data (shown by the top
 * bar and the call panel); the sessions of JsSIP stay outside of it.
 */
export const whatsappSoftphoneService = {
    dependencies: ["notification", "bus_service", "action"],
    start(env, { notification, bus_service: busService, action }) {
        const state = proxy({
            enabled: false,
            available: false,
            status: "off", // off, connecting, ready, error
            needsGesture: false,
            incoming: null, // {callId, name, number, channelId, account, previousCalls}
            active: null, // {callId, name, number, channelId, startedAt, muted, lost}
            message: "",
        });
        let config = null;
        let ua = null;
        let incomingSession = null;
        let activeSession = null;
        let audioContext = null;
        let ringer = null;
        let titleTimer = null;
        let originalTitle = "";
        let mediaLostTimer = null;
        let restarting = false;
        const remoteAudio = new Audio();
        remoteAudio.autoplay = true;

        // === SOUND === //

        function unlockAudio() {
            try {
                audioContext = audioContext || new (browser.AudioContext || browser.webkitAudioContext)();
                if (audioContext.state === "suspended") {
                    audioContext.resume();
                }
                state.needsGesture = audioContext.state !== "running";
            } catch {
                state.needsGesture = false;
            }
        }

        function ringOnce() {
            if (!audioContext || audioContext.state !== "running") {
                return;
            }
            const now = audioContext.currentTime;
            for (const [start, stop] of [[0, 0.4], [0.6, 1.0]]) {
                for (const frequency of [440, 480]) {
                    const oscillator = audioContext.createOscillator();
                    const gain = audioContext.createGain();
                    oscillator.frequency.value = frequency;
                    gain.gain.value = 0.08;
                    oscillator.connect(gain).connect(audioContext.destination);
                    oscillator.start(now + start);
                    oscillator.stop(now + stop);
                }
            }
        }

        function startRinging() {
            stopRinging();
            ringOnce();
            ringer = browser.setInterval(ringOnce, 3000);
            originalTitle = document.title;
            let flip = false;
            titleTimer = browser.setInterval(() => {
                flip = !flip;
                document.title = flip ? _t("Call: %s", state.incoming?.name || "") : originalTitle;
            }, 1000);
            if (browser.Notification?.permission === "granted" && document.hidden) {
                try {
                    const notice = new browser.Notification(_t("WhatsApp call"), {
                        body: state.incoming?.name || state.incoming?.number || "",
                        tag: "whatsapp-call",
                    });
                    notice.onclick = () => browser.focus();
                } catch {
                    // notifications refused by the browser: the ringing and the panel remain
                }
            }
        }

        function stopRinging() {
            if (ringer) {
                browser.clearInterval(ringer);
                ringer = null;
            }
            if (titleTimer) {
                browser.clearInterval(titleTimer);
                document.title = originalTitle || document.title;
                titleTimer = null;
            }
        }

        // === CALL SERVER === //

        async function loadConfig() {
            try {
                config = await rpc("/whatsapp/call/softphone/config", {}, { silent: true });
            } catch {
                config = null;
            }
            state.enabled = Boolean(config);
            state.available = Boolean(config?.available);
            return config;
        }

        async function connect() {
            if (!config) {
                return;
            }
            await loadJS(JSSIP_URL);
            const JsSIP = browser.JsSIP;
            if (ua) {
                ua.stop();
            }
            state.status = "connecting";
            ua = new JsSIP.UA({
                sockets: [new JsSIP.WebSocketInterface(config.wss)],
                uri: config.uri,
                password: config.password,
                display_name: config.display_name,
                register: true,
                register_expires: 120,
                session_timers: false,
                connection_recovery_min_interval: 2,
                connection_recovery_max_interval: 30,
                user_agent: "OCD Odoo",
            });
            ua.on("registered", () => {
                state.status = "ready";
                state.message = "";
            });
            ua.on("unregistered", () => {
                state.status = state.available ? "connecting" : "off";
            });
            ua.on("disconnected", () => {
                if (state.available) {
                    state.status = "connecting";
                }
            });
            ua.on("registrationFailed", async (event) => {
                state.status = "error";
                state.message = _t("The call server refused the connection (%s).", event.cause || "");
                // a password changed in Odoo: read it again once
                if (!restarting && /auth/i.test(String(event.cause))) {
                    restarting = true;
                    await loadConfig();
                    if (state.available) {
                        await connect();
                    }
                    restarting = false;
                }
            });
            ua.on("newRTCSession", ({ originator, session, request }) => {
                if (originator !== "remote") {
                    return;
                }
                onIncoming(session, request);
            });
            ua.start();
        }

        function disconnect() {
            if (ua) {
                ua.stop();
                ua = null;
            }
            state.status = "off";
        }

        // === CALLS === //

        function callInfo(session, request) {
            const identity = session.remote_identity;
            const callId = parseInt(request?.getHeader?.("X-OCD-Call") || "0", 10) || false;
            // no number when the customer hides it (FreeSWITCH then gives 0000000000)
            const digits = String(identity?.uri?.user || "").replace(/\D/g, "");
            return {
                callId,
                name: identity?.display_name || "",
                number: digits && !/^0+$/.test(digits) ? `+${digits}` : "",
                channelId: false,
                account: "",
                previousCalls: 0,
            };
        }

        async function onIncoming(session, request) {
            if (activeSession || incomingSession) {
                // one call at a time: the call server rings the free colleagues
                session.terminate({ status_code: 486, reason_phrase: "Busy Here" });
                return;
            }
            incomingSession = session;
            state.incoming = callInfo(session, request);
            state.message = "";
            session.on("failed", (event) => {
                if (session !== incomingSession) {
                    return;
                }
                incomingSession = null;
                stopRinging();
                const elsewhere = /elsewhere/i.test(String(event.message?.getHeader?.("Reason") || ""));
                state.message = elsewhere ? _t("Answered by a colleague.") : "";
                state.incoming = null;
            });
            session.on("ended", () => onEnded(session));
            startRinging();
            if (state.incoming.callId) {
                try {
                    const info = await rpc("/whatsapp/call/softphone/info", { call_id: state.incoming.callId }, { silent: true });
                    if (info && state.incoming && state.incoming.callId === info.id) {
                        Object.assign(state.incoming, {
                            name: info.name || state.incoming.name,
                            number: info.number || state.incoming.number,
                            channelId: info.channel_id,
                            account: info.account,
                            previousCalls: info.previous_calls,
                        });
                    }
                } catch {
                    // Odoo slow or unreachable: the name given by the call server is shown
                }
            }
        }

        function watchMedia(session) {
            const connection = session.connection;
            if (!connection) {
                return;
            }
            connection.addEventListener("track", (event) => {
                remoteAudio.srcObject = event.streams[0] || new MediaStream([event.track]);
                remoteAudio.play().catch(() => {});
            });
            connection.addEventListener("iceconnectionstatechange", () => {
                const ice = connection.iceConnectionState;
                if (ice === "disconnected" || ice === "failed") {
                    if (state.active) {
                        state.active.lost = true;
                    }
                    browser.clearTimeout(mediaLostTimer);
                    mediaLostTimer = browser.setTimeout(() => {
                        if (session === activeSession && ["disconnected", "failed"].includes(connection.iceConnectionState)) {
                            state.message = _t("Connection lost: the call comes back to you or goes to a colleague.");
                            try {
                                // a cause of network for the call server: the customer waits
                                // for the call to come back (a plain hang-up ends their call)
                                session.terminate({
                                    extraHeaders: ['Reason: Q.850;cause=41;text="media lost"'],
                                });
                            } catch {
                                onEnded(session);
                            }
                        }
                    }, MEDIA_LOST_MS);
                } else if (ice === "connected" || ice === "completed") {
                    browser.clearTimeout(mediaLostTimer);
                    if (state.active) {
                        state.active.lost = false;
                    }
                }
            });
        }

        function onEnded(session) {
            if (session === incomingSession) {
                incomingSession = null;
                state.incoming = null;
                stopRinging();
            }
            if (session === activeSession) {
                activeSession = null;
                state.active = null;
                remoteAudio.srcObject = null;
                browser.clearTimeout(mediaLostTimer);
                if (!state.available) {
                    // the agent stopped taking the calls during this one
                    disconnect();
                }
            }
        }

        async function answer() {
            const session = incomingSession;
            if (!session) {
                return;
            }
            unlockAudio();
            stopRinging();
            incomingSession = null;
            activeSession = session;
            state.active = { ...state.incoming, startedAt: Date.now(), muted: false, lost: false };
            state.incoming = null;
            session.on("peerconnection", () => watchMedia(session));
            try {
                session.answer({
                    mediaConstraints: { audio: true, video: false },
                    pcConfig: { iceServers: config.ice_servers || [], iceTransportPolicy: "all" },
                });
            } catch (error) {
                notification.add(_t("The call could not be answered: %s", error.message || error), { type: "danger" });
                onEnded(session);
                return;
            }
            if (session.connection) {
                watchMedia(session);
            }
            session.on("failed", (event) => {
                if (event.cause === browser.JsSIP?.C?.causes?.USER_DENIED_MEDIA_ACCESS) {
                    notification.add(
                        _t("The browser refuses the microphone: allow it for this site, then answer again."),
                        { type: "danger", sticky: true }
                    );
                }
                onEnded(session);
            });
        }

        function decline() {
            const session = incomingSession;
            if (!session) {
                return;
            }
            const callId = state.incoming?.callId;
            session.terminate({ status_code: 603, reason_phrase: "Decline" });
            onEnded(session);
            if (callId) {
                rpc("/whatsapp/call/softphone/declined", { call_id: callId }, { silent: true }).catch(() => {});
            }
        }

        function hangup() {
            if (activeSession) {
                activeSession.terminate();
                onEnded(activeSession);
            }
        }

        function toggleMute() {
            if (!activeSession || !state.active) {
                return;
            }
            if (state.active.muted) {
                activeSession.unmute({ audio: true });
            } else {
                activeSession.mute({ audio: true });
            }
            state.active.muted = !state.active.muted;
        }

        function openConversation(channelId) {
            if (!channelId) {
                return;
            }
            action.doAction({
                type: "ir.actions.client",
                tag: "mail.action_discuss",
                params: { active_id: `discuss.channel_${channelId}` },
            });
        }

        async function setAvailable(available) {
            unlockAudio();
            if (available && browser.Notification?.permission === "default") {
                browser.Notification.requestPermission().catch(() => {});
            }
            const result = await rpc("/whatsapp/call/softphone/available", { available });
            if (!result) {
                state.enabled = false;
                disconnect();
                return;
            }
            config = result;
            state.available = Boolean(result.available);
            if (state.available) {
                await connect();
            } else if (!activeSession) {
                disconnect();
            }
        }

        // === START === //

        browser.addEventListener("beforeunload", (event) => {
            if (activeSession) {
                event.preventDefault();
                event.returnValue = "";
            }
        });
        browser.addEventListener("pointerdown", () => {
            if (state.needsGesture) {
                unlockAudio();
            }
        });
        busService.subscribe("whatsapp.call/update", (payload) => {
            if (payload.ended_at_meta) {
                // the customer hung up (told by Meta) and the call server did not see it: the
                // phone hangs up, which ends the call on the call server too
                if (activeSession && state.active?.callId === payload.id) {
                    hangup();
                } else if (incomingSession && state.incoming?.callId === payload.id) {
                    const session = incomingSession;
                    session.terminate({ status_code: 487, reason_phrase: "Request Terminated" });
                    onEnded(session);
                }
                return;
            }
            if (state.incoming && payload.id === state.incoming.callId && payload.state === "answered" && payload.user_name) {
                state.message = _t("Answered by %s.", payload.user_name);
            }
        });

        (async () => {
            if (await loadConfig()) {
                if (state.available) {
                    unlockAudio();
                    await connect();
                }
            }
        })();

        Object.assign(state, { answer, decline, hangup, toggleMute, openConversation, setAvailable });
        return state;
    },
};

registry.category("services").add("whatsapp_softphone", whatsappSoftphoneService);
