// pages/CallPage.jsx — face-to-face tutoring over WebRTC.
//
// Flow for a matched session:
//   1. both parties open /call/<sessionId>
//   2. each connects to the signaling room and starts its own camera
//   3. the *initiator* (student, by role) sends an offer; the other answers
//   4. either side can switch quality (low/medium/high) live; the mediaserver
//      can also push "low" when the student's RTCP losses climb
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
  const token = useStore(() => getAccessToken());
  const role = useStore((s) => s.user?.user?.role || "student");

  const [mode, setMode] = useState("medium");
  const [state, setState] = useState("connecting"); // connecting|local|ringing|live
  const [error, setError] = useState("");
  const [audioOnly, setAudioOnly] = useState(false);

  const localRef = useRef(null);
  const remoteRef = useRef(null);
  const peerRef = useRef(null);
  const signalRef = useRef(null);
  const peerReadyRef = useRef(false);
  const callStartedRef = useRef(false);

  const start = useCallback(async () => {
    if (callStartedRef.current) return;
    callStartedRef.current = true;

    // Fire up signaling first.
    const signal = new SignalClient({ sessionId, token, onMessage: onSignal });
    signalRef.current = signal;
    try {
      await signal.connect();
    } catch {
      setError("Could not reach the tutoring server. Check your connection.");
      setState("live");
      return;
    }

    const ice = await (async () => {
      try {
        const { data } = await api.get("/api/v1/tutoring/ice/");
        return data.iceServers;
      } catch {
        return [{ urls: "stun:stun.l.google.com:19302" }];
      }
    })();

    const peer = new PeerSession({
      signal,
      iceServers: ice,
      mode: "medium",
      onRemoteStream: (stream) => {
        if (remoteRef.current) {
          remoteRef.current.srcObject = stream;
          remoteRef.current.play().catch(() => {});
        }
      },
    });
    peerRef.current = peer;

    // Mark the session active so both sides proceed.
    try {
      await api.post(`/api/v1/tutoring/sessions/${sessionId}/start/`, { mode: "medium" });
    } catch { /* already active */ }

    try {
      const local = await peer.startLocal({ audioOnly });
      if (localRef.current) localRef.current.srcObject = local;
      setState("local");

      if (peer.pc) {
        peer.pc.onnegotiationneeded = () => {
          // Only the designated initiator drives signalling to avoid glare.
          if (role !== "student") return;
          peer.makeOffer().catch(() => {});
        };
      }
      await peer.makeOffer().catch(() => {});
    } catch (e) {
      setError("No microphone/camera permission. Video calls need camera access.");
      setState("live");
    }
  }, [sessionId, token, role, audioOnly]); // eslint-disable-line

  function onSignal(msg) {
    const peer = peerRef.current;
    if (!peer) return;
    if (msg.type === "offer" && role !== "student") {
      peer.acceptOffer(msg.payload.sdp).then(() => setState("live")).catch(() => {});
    } else if (msg.type === "answer") {
      peer.acceptAnswer(msg.payload.sdp).then(() => setState("live")).catch(() => {});
    } else if (msg.type === "ice" && msg.payload?.candidate) {
      peer.addIce(msg.payload.candidate).catch(() => {});
    } else if (msg.type === "mode" && msg.payload?.mode) {
      switchModeUi(msg.payload.mode);
    }
  }

  const switchModeUi = (m) => {
    setMode(m);
    peerRef.current?.applyMode && peerRef.current.applyMode(m);
  };

  const toggleQuality = (m) => {
    switchModeUi(m);
    signalRef.current?.send({ type: "mode", mode: m });
  };

  useEffect(() => {
    if (state === "connecting") start();
    // eslint-disable-next-line
  }, [state]);

  useEffect(() => () => { peerRef.current?.close(); signalRef.current?.close(); }, []);

  return (
    <div className="call">
      <div className="call-bar">
        <span className="pill">Session #{sessionId}</span>
        <span className={`pill ${state === "live" ? "live" : ""}`}>
          {state === "live" ? "LIVE" : state}
        </span>
        <div className="quality">
          {Object.keys(MODES).map((m) => (
            <button key={m} className={mode === m ? "btn primary sm" : "btn sm"} onClick={() => toggleQuality(m)}>
              {MODES[m].label}
            </button>
          ))}
        </div>
        <button className="btn sm" onClick={() => setAudioOnly((a) => !a)}>
          {audioOnly ? "Audio only" : "Mute camera"}
        </button>
      </div>

      <div className="call-frames">
        <video ref={remoteRef} className="remote" autoPlay playsInline muted={false} />
        <video ref={localRef} className="local" autoPlay playsInline muted />
      </div>

      {error && <p className="error">{error}</p>}
      {state !== "connecting" && (
        <button className="btn danger" onClick={() => endCall(sessionId)}>End session</button>
      )}
    </div>
  );
}

async function endCall(sessionId) {
  try {
    await api.post(`/api/v1/tutoring/sessions/${sessionId}/end/`, { rating: 5 });
  } catch { /* offline rating: queue it */ }
  location.href = "/#/dashboard";
}