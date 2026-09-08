// pages/CallPage.jsx — face-to-face tutoring over WebRTC.
//
// Flow for a matched session (Zoom-style):
//   1. both parties open /call/<sessionId> when their scheduled window starts
//   2. each connects to the signaling room and starts its own camera
//   3. the page shows a lobby ("waiting for your tutor…") until the peer joins
//   4. the student (initiator) drives the offer; the teacher answers. Collisions
//      are handled "perfect negotiation" style so simultaneous joins never glare.
//   5. a watchdog renegotiates if the call hasn't come up after a few seconds
//
// On links that can't carry video the app falls back to audio-only — keeping
// the conversation is what matters.

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { SignalClient } from "../services/signal";
import { PeerSession, MODES } from "../services/webrtc";
import { api, getAccessToken } from "../api/client";
import { useStore } from "../store/app";

export default function CallPage() {
  const { sessionId } = useParams();
  const role = useStore((s) => s.user?.user?.role || "student");
  const token = getAccessToken();

  const [mode, setMode] = useState("medium");
  const [state, setState] = useState("connecting"); // connecting|lobby|negotiating|live|ended
  const [error, setError] = useState("");
  const [wantAudio, setWantAudio] = useState(false);
  const [schedule, setSchedule] = useState(null);

  const localRef = useRef(null);
  const remoteRef = useRef(null);
  const peerRef = useRef(null);
  const signalRef = useRef(null);
  const partnerRef = useRef(false);
  const startedRef = useRef(false);
  const offeredRef = useRef(false);
  const retryRef = useRef(0);
  const watchdogRef = useRef(null);

  const sendPeerOrOffer = useCallback(() => {
    // The student drives negotiation; the teacher simply answers incoming offers.
    const peer = peerRef.current;
    if (!peer || peerRef.current?.closed) return;
    if (role === "student" && partnerRef.current) {
      peer.makeOffer().catch(() => {});
      armWatchdog();
    }
  }, [role]);

  const armWatchdog = useCallback(() => {
    if (watchdogRef.current) clearTimeout(watchdogRef.current);
    watchdogRef.current = setTimeout(() => {
      const peer = peerRef.current;
      if (!peer || peer.isLive() || state === "live" || state === "ended") return;
      if (retryRef.current >= 2) {
        setError("Could not connect a video session. Try rejoining.");
        setState("ended");
        return;
      }
      // Tear down and rebuild the peer, then re-negotiate (cold-start recovery).
      retryRef.current += 1;
      peer.close();
      bootstrapPeer().then(() => sendPeerOrOffer()).catch(() => {});
    }, 10000);
  }, [role, state]);

  const bootstrapPeer = useCallback(async () => {
    const ice = await (async () => {
      try {
        const { data } = await api.get("/api/v1/tutoring/ice/");
        return data.iceServers;
      } catch {
        return [{ urls: "stun:stun.l.google.com:19302" }];
      }
    })();

    const peer = new PeerSession({
      signal: signalRef.current,
      iceServers: ice,
      mode,
      isPolite: role !== "student",
      onRemoteStream: (stream) => {
        if (remoteRef.current) {
          remoteRef.current.srcObject = stream;
          remoteRef.current.play().catch(() => {});
        }
      },
    });
    peerRef.current = peer;

    try {
      const local = await peer.startLocal({ audioOnly: wantAudio });
      if (localRef.current) localRef.current.srcObject = local;
    } catch {
      setError("No microphone/camera permission. Video calls need camera access.");
      setState("ended");
      return;
    }

    // Mark the session active so the other side's presence turns on.
    try {
      await api.post(`/api/v1/tutoring/sessions/${sessionId}/start/`, { mode: "medium" });
    } catch { /* already active */ }
    setState((s) => (s === "ended" ? s : partnerRef.current ? "negotiating" : "lobby"));
  }, [sessionId, mode, wantAudio, role]);

  const start = useCallback(async () => {
    if (startedRef.current) return;
    startedRef.current = true;

    const signal = new SignalClient({
      sessionId,
      token,
      getToken: getAccessToken,
      onMessage: onSignal,
    });
    signalRef.current = signal;
    try {
      await signal.connect();
    } catch {
      setError("Could not reach the tutoring server. Check your connection.");
      setState("ended");
      return;
    }

    await bootstrapPeer();
    // If the partner is already waiting, kick off negotiation immediately.
    sendPeerOrOffer();
  }, [sessionId, token, bootstrapPeer, sendPeerOrOffer]);

  function onSignal(msg) {
    if (msg.type === "welcome") {
      if (msg.schedule) setSchedule(msg.schedule);
      return;
    }
    if (msg.type === "peer_joined") {
      const first = !partnerRef.current;
      partnerRef.current = true;
      if (first) {
        if (state === "lobby" || state === "connecting") {
          setState("negotiating");
          sendPeerOrOffer();
        }
      }
      return;
    }
    if (msg.type === "peer_left") {
      partnerRef.current = false;
      if (state === "live") {
        setError("The other person left the session.");
        setState("ended");
        endCall(sessionId);
      } else {
        setState("lobby");
      }
      return;
    }
    const peer = peerRef.current;
    if (!peer) return;
    peer.handleSignal(msg);
    if ((msg.type === "answer" || msg.type === "offer")) {
      setState("negotiating");
    }
    if (peer.isLive()) {
      setState("live");
      if (watchdogRef.current) clearTimeout(watchdogRef.current);
    }
  }

  // Mark LIVE from the connection state itself, not only message arrivals.
  useEffect(() => {
    const iv = setInterval(() => {
      if (peerRef.current?.isLive() && state !== "live" && state !== "ended") {
        setState("live");
        if (watchdogRef.current) clearTimeout(watchdogRef.current);
      }
    }, 1500);
    return () => clearInterval(iv);
  }, [state]);

  useEffect(() => {
    if (state === "connecting") start();
  }, [state, start]);

  useEffect(
    () => () => {
      peerRef.current?.close();
      signalRef.current?.close();
      if (watchdogRef.current) clearTimeout(watchdogRef.current);
    },
    []
  );

  const switchMode = (m) => {
    setMode(m);
    if (peerRef.current) peerRef.current.applyMode(m);
    signalRef.current?.send({ type: "mode", mode: m });
  };

  const scheduleLabel = schedule
    ? `${new Date(schedule.scheduled_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} · ${schedule.duration_minutes} min`
    : "";

  return (
    <div className={`call ${state === "live" ? "call-live" : ""}`}>
      <div className="call-bar">
        <span className="pill">Session #{sessionId}{scheduleLabel ? ` · ${scheduleLabel}` : ""}</span>
        <span className={`pill ${state === "live" ? "live" : ""}`}>
          {state === "live" ? "LIVE" : state === "lobby" ? "Waiting…" : state}
        </span>
        <div className="quality">
          {Object.keys(MODES).map((m) => (
            <button key={m} className={mode === m ? "btn primary sm" : "btn sm"} onClick={() => switchMode(m)}>
              {MODES[m].label}
            </button>
          ))}
        </div>
        {state !== "live" && state !== "ended" && (
          <button className="btn sm" onClick={() => setWantAudio((a) => !a)}>
            {wantAudio ? "📞 Audio call" : "🎥 Video call"}
          </button>
        )}
      </div>

      <div className="call-frames">
        <video ref={remoteRef} className="remote" autoPlay playsInline muted={false} hidden={!state.includes("live") && state !== "negotiating" && state !== "lobby"} />
        <video ref={localRef} className="local" autoPlay playsInline muted hidden={state === "connecting" || state === "ended"} />
      </div>

      {state === "connecting" && <p className="hint">🔌 Connecting to the tutoring room…</p>}
      {state === "lobby" && (
        <div className="card lobby">
          <div className="spinner" aria-hidden />
          <h3>{role === "teacher" ? `Waiting for your student to join…` : `Waiting for your tutor to join…`}</h3>
          <p className="muted small">Your camera is on. The session will start automatically when they arrive.</p>
        </div>
      )}
      {state === "negotiating" && <p className="hint">🔁 Partner joined — establishing the video link…</p>}

      {error && <p className="error">{error}</p>}
      {state !== "connecting" && state !== "ended" && (
        <button className="btn danger" onClick={() => endCall(sessionId)}>End session</button>
      )}
    </div>
  );
}

async function endCall(sessionId) {
  try {
    await api.post(`/api/v1/tutoring/sessions/${sessionId}/end/`, { rating: 5 });
  } catch { /* offline rating: queue it */ }
  location.hash = "#/tutors";
}