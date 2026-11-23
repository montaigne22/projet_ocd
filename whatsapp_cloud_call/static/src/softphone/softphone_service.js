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
// JsSIP sends the answer only once the browser has gathered all its network addresses (ICE); a
// STUN or TURN server that does not answer (UDP blocked by a firewall, relay stopped) holds it
// 10 to 40 seconds, and the call server stops ringing after 20 seconds and rings again (answered,
// but it rings again). The call server takes no address sent later (no trickle ICE): the answer
// leaves with the address of the relay (TURN), the way of the voice when the direct one is
// blocked; with only the public address (STUN), it waits for the relay a little; at most after
// ICE_GATHERING_MS (a relay over TLS far away takes 2 seconds and more).
const ICE_GATHERING_MS = 8000;
const ICE_RELAY_WAIT_MS = 3000;
// The browser still asks for the microphone after this time: the agent is shown where to allow it.
const MICROPHONE_HINT_MS = 1500;
// Shown in the menu of the phone and in its diagnostic: the version of the module.
const SOFTPHONE_VERSION = "20.0.1.9.2";
// The phone hangs up because the call ended at Meta (told by Odoo before the call server): the
// call server counts it as ended by the customer (scripts/ocd/queue.lua, ENDED_AT_META)
const ENDED_AT_META_REASON = 'Reason: Q.850;cause=31;text="ended at Meta"';

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
            // connecting: answered, the call not established yet (no "In call" before it is)
            // askingMicrophone: the browser waits for the agent to allow the microphone
            active: null, // {callId, name, number, channelId, startedAt, muted, lost, connecting, askingMicrophone}
            message: "",
            // microphone of the browser: "granted", "prompt" (Chrome will ask), "denied"
            microphone: "unknown",
            version: SOFTPHONE_VERSION,
        });
        let config = null;
        let ua = null;
        let incomingSession = null;
        let activeSession = null;
        let localStream = null;
        let audioContext = null;
        let ringer = null;
        let titleTimer = null;
        let originalTitle = "";
        let mediaLostTimer = null;
        let restarting = false;
        const remoteAudio = new Audio();
        remoteAudio.autoplay = true;

        // === SOUND === //

        // === MICROPHONE === //

        async function microphonePermission() {
            try {
                const status = await browser.navigator.permissions.query({ name: "microphone" });
                status.onchange = () => {
                    state.microphone = status.state;
                };
                return status.state;
            } catch {
                return "unknown";
            }
        }

        /** The microphone allowed when the agent starts taking the calls (Chrome asks then),
         * not while a call rings: a question of Chrome left unanswered holds the answer of the
         * call, and the call server rings again after 20 seconds. */
        async function askMicrophone() {
            try {
                const stream = await browser.navigator.mediaDevices.getUserMedia({ audio: true });
                stream.getTracks().forEach((track) => track.stop());
                state.microphone = "granted";
            } catch {
                state.microphone = await microphonePermission();
                if (state.microphone !== "granted") {
                    state.microphone = "denied";
                }
            }
        }

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
                ringingSince: Date.now(),
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
            if (!connection || session.ocdWatched) {
                return;
            }
            session.ocdWatched = true;
            connection.addEventListener("track", (event) => {
                remoteAudio.srcObject = event.streams[0] || new MediaStream([event.track]);
                remoteAudio.play().catch(() => {});
            });
            connection.addEventListener("iceconnectionstatechange", () => {
                const ice = connection.iceConnectionState;
                session.ocdNote?.(`network ${ice}`);
                if (ice === "disconnected" || ice === "failed") {
                    if (state.active) {
                        state.active.lost = true;
                    }
                    browser.clearTimeout(mediaLostTimer);
                    mediaLostTimer = browser.setTimeout(() => {
                        if (session === activeSession && ["disconnected", "failed"].includes(connection.iceConnectionState)) {
                            state.message = _t("Connection lost: the call comes back to you or goes to a colleague.");
                            session.ocdNote?.("connection lost: hung up");
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
                localStream?.getTracks().forEach((track) => track.stop());
                localStream = null;
                remoteAudio.srcObject = null;
                browser.clearTimeout(mediaLostTimer);
                if (!state.available) {
                    // the agent stopped taking the calls during this one
                    disconnect();
                }
            }
        }

        // === DIAGNOSTIC AND NETWORK ADDRESSES (answer and call of the company) === //

        /** The diagnostic of a call by this phone, kept on the call in Odoo (phone_trace). */
        function makeTracker(callId, start) {
            const begun = Date.now();
            const trace = [`phone ${SOFTPHONE_VERSION}`, start];
            let sent = false;
            const note = (text) => trace.push(`${Date.now() - begun} ms ${text}`);
            const send = (end) => {
                if (sent) {
                    return;
                }
                sent = true;
                note(end);
                if (callId) {
                    rpc("/whatsapp/call/softphone/trace", { call_id: callId, trace: trace.join("; ") },
                        { silent: true }).catch(() => {});
                }
            };
            return { note, send };
        }

        /** The network addresses of a call: its SDP leaves with the relay address, else 3
         * seconds after the public address, at most after ICE_GATHERING_MS (see above). */
        function iceHandler(note, label) {
            let iceTimer = null;
            let relayWait = null;
            let publicAddress = false;
            const seenTypes = new Set();
            const ready = (event, why) => {
                note(`${label} sent (${why})`);
                event.ready();
            };
            return (event) => {
                const type = event.candidate?.type;
                if (type && !seenTypes.has(type)) {
                    seenTypes.add(type);
                    note(`address ${type}${event.candidate?.protocol ? " " + event.candidate.protocol : ""}`);
                }
                if (type === "relay") {
                    browser.clearTimeout(iceTimer);
                    browser.clearTimeout(relayWait);
                    ready(event, "relay");
                    return;
                }
                if (type === "srflx") {
                    publicAddress = true;
                    relayWait ||= browser.setTimeout(() => ready(event, "public address, no relay"), ICE_RELAY_WAIT_MS);
                }
                if (!iceTimer) {
                    iceTimer = browser.setTimeout(() => {
                        if (!publicAddress) {
                            // only the masked address of the computer (".local"): the call
                            // server cannot send the voice back, it refuses the call
                            notification.add(
                                _t("The voice relay of the call server (STUN/TURN, ports 3478 and 5349) does not answer: the call cannot go through. Tell the administrator (coturn on the call server, firewall)."),
                                { type: "danger", sticky: true }
                            );
                        }
                        ready(event, publicAddress ? "public address" : "no public address");
                    }, ICE_GATHERING_MS);
                }
            };
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
            // the diagnostic of this answer, kept on the call in Odoo (whatsapp.call phone_trace)
            const rung = state.incoming?.ringingSince ? Date.now() - state.incoming.ringingSince : "?";
            const tracker = makeTracker(state.incoming?.callId, `answered ${rung} ms after the ring`);
            const sendTrace = tracker.send;
            session.ocdNote = tracker.note;
            session.on("confirmed", () => session.ocdNote("established"));
            session.on("ended", (event) => sendTrace(`ended: ${event.cause} (${event.originator})`));
            state.active = {
                ...state.incoming, startedAt: Date.now(), muted: false, lost: false, connecting: true,
                askingMicrophone: false,
            };
            state.incoming = null;
            // "In call" once the call server confirms the answer (ACK), the time counted from then
            session.on("confirmed", () => {
                if (session === activeSession && state.active) {
                    state.active.connecting = false;
                    state.active.startedAt = Date.now();
                }
            });
            session.on("failed", (event) => {
                sendTrace(`failed: ${event.cause} (${event.originator})`);
                if (event.cause === browser.JsSIP?.C?.causes?.USER_DENIED_MEDIA_ACCESS) {
                    notification.add(
                        _t("The browser refuses the microphone: allow it for this site, then answer again."),
                        { type: "danger", sticky: true }
                    );
                }
                onEnded(session);
            });
            // the microphone first: while the browser asks the agent, nothing goes to the call
            // server (it rings again after 20 seconds); the agent is shown where to allow it
            const asking = browser.setTimeout(() => {
                if (session === activeSession && state.active) {
                    state.active.askingMicrophone = true;
                }
            }, MICROPHONE_HINT_MS);
            let stream = null;
            try {
                stream = await browser.navigator.mediaDevices.getUserMedia({ audio: true, video: false });
                state.microphone = "granted";
                session.ocdNote("microphone");
            } catch (error) {
                state.microphone = "denied";
                session.ocdNote(`microphone refused (${error?.name || error})`);
            }
            browser.clearTimeout(asking);
            if (session !== activeSession || session.isEnded()) {
                // the call ended meanwhile (customer gone, rung again)
                stream?.getTracks().forEach((track) => track.stop());
                sendTrace("ended while the microphone was asked");
                return;
            }
            if (!stream) {
                notification.add(
                    _t("The browser refuses the microphone: allow it for this site, then answer again."),
                    { type: "danger", sticky: true }
                );
                try {
                    session.terminate({ status_code: 480, reason_phrase: "Microphone refused" });
                } catch {
                    // already ended
                }
                const callId = state.active?.callId;
                sendTrace("answer refused: no microphone");
                onEnded(session);
                if (callId) {
                    // as declined: this call is not rung again for this agent
                    rpc("/whatsapp/call/softphone/declined", { call_id: callId }, { silent: true }).catch(() => {});
                }
                return;
            }
            state.active.askingMicrophone = false;
            localStream = stream;
            session.on("peerconnection", () => watchMedia(session));
            session.on("icecandidate", iceHandler(tracker.note, "answer"));
            try {
                session.answer({
                    mediaStream: stream,
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
        }

        // === CALLS OF THE COMPANY === //

        /** Why a call of the company did not go through, for the agent. */
        function dialFailure(event) {
            const C = browser.JsSIP?.C?.causes || {};
            if (event.originator === "local" && event.cause === C.CANCELED) {
                return ""; // the agent hung up while it rang
            }
            if (event.message?.status_code === 403) {
                return _t("The call did not leave: %s", event.message.reason_phrase || "");
            }
            if ([C.BUSY, C.REJECTED].includes(event.cause)) {
                return _t("The customer declined the call.");
            }
            if ([C.UNAVAILABLE, C.NO_ANSWER, C.REQUEST_TIMEOUT].includes(event.cause)) {
                return _t("No answer from the customer.");
            }
            return _t("The call did not go through (%s).", event.cause);
        }

        /** Call a customer through WhatsApp (prepared by Odoo, whatsapp_action_call): the call
         * server checks the call with Odoo and calls the customer through Meta; the agent hears
         * it ring, then the customer. */
        async function dial({ call_id: callId, name, number }) {
            const fail = (reason, text) => {
                if (text) {
                    notification.add(text, { type: "warning" });
                }
                rpc("/whatsapp/call/softphone/dial_failed", { call_id: callId, reason }, { silent: true }).catch(() => {});
            };
            if (!ua || state.status !== "ready") {
                return fail("PHONE_NOT_CONNECTED",
                    _t("Take the WhatsApp calls first (phone of the top bar): the call leaves from it."));
            }
            if (activeSession || incomingSession) {
                return fail("PHONE_BUSY", _t("Finish the current call first."));
            }
            unlockAudio();
            const tracker = makeTracker(callId, "call of the company");
            let stream = null;
            try {
                stream = await browser.navigator.mediaDevices.getUserMedia({ audio: true, video: false });
                state.microphone = "granted";
                tracker.note("microphone");
            } catch (error) {
                state.microphone = "denied";
                tracker.send(`microphone refused (${error?.name || error})`);
                return fail("MICROPHONE",
                    _t("The browser refuses the microphone: allow it for this site, then call again."));
            }
            if (activeSession || incomingSession) {
                // a call came meanwhile
                stream.getTracks().forEach((track) => track.stop());
                return fail("PHONE_BUSY", _t("Finish the current call first."));
            }
            localStream = stream;
            state.message = "";
            state.active = {
                callId, name, number, outgoing: true, startedAt: Date.now(), muted: false, lost: false,
                connecting: true, ringing: false, askingMicrophone: false,
            };
            let session = null;
            const established = () => {
                tracker.note("established");
                if (session && session === activeSession && state.active) {
                    state.active.connecting = false;
                    state.active.startedAt = Date.now();
                }
            };
            session = ua.call(`sip:out${callId}@${config.uri.split("@")[1]}`, {
                mediaStream: stream,
                pcConfig: { iceServers: config.ice_servers || [], iceTransportPolicy: "all" },
                extraHeaders: [`X-OCD-Call: ${callId}`],
                eventHandlers: {
                    icecandidate: iceHandler(tracker.note, "call"),
                    progress: () => {
                        tracker.note("ringing");
                        if (state.active?.outgoing) {
                            state.active.ringing = true;
                        }
                    },
                    confirmed: established,
                    ended: (event) => {
                        tracker.send(`ended: ${event.cause} (${event.originator})`);
                        onEnded(session);
                    },
                    failed: (event) => {
                        tracker.send(`failed: ${event.cause} (${event.originator})`);
                        state.message = dialFailure(event);
                        onEnded(session);
                    },
                },
            });
            activeSession = session;
            session.ocdNote = tracker.note;
            watchMedia(session);
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

        /** Hang up the call in progress; the reason goes to the diagnostic of the call. */
        function hangup(reason = "hung up by the agent", options = {}) {
            if (activeSession) {
                activeSession.ocdNote?.(reason);
                activeSession.terminate(options);
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
                // not awaited: the agent connects while Chrome asks
                askMicrophone();
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
                    // the cause tells the call server that the customer ended the call (Q.850
                    // 31, NORMAL_UNSPECIFIED there), not the agent
                    hangup("ended at Meta, told by Odoo before the call server", {
                        extraHeaders: [ENDED_AT_META_REASON],
                    });
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
                    state.microphone = await microphonePermission();
                    if (state.microphone !== "denied") {
                        askMicrophone();
                    }
                    await connect();
                }
            }
        })();

        Object.assign(state, { answer, decline, dial, hangup, toggleMute, openConversation, setAvailable });
        return state;
    },
};

registry.category("services").add("whatsapp_softphone", whatsappSoftphoneService);

// "Call through WhatsApp" (conversation, call): the call prepared by Odoo leaves from this phone
registry.category("actions").add("whatsapp_call_dial", (env, action) => {
    env.services.whatsapp_softphone.dial(action.params || {});
});
