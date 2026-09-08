// services/webrtc.js — camera + mic setup with bandwidth-aware presets, and a
// glare-free RTCPeerConnection using the "perfect negotiation" pattern.
//
// The "most important part" of the app: face-to-face video with a tutor in
// another country. Everything is tuned so the call survives 2G:
//
//   low    -> 320x240 @ 10fps, ~120 kbps video (audio always preserved)
//   medium -> 640x480 @ 15fps, ~350 kbps
//   high   -> 1280x720 @ 30fps, up to 1 Mbps (only sane links)
//
// The mediaserver or the signal relay can push {"type":"mode",...} to drop
// quality live when RTCP loss climbs.
//
// Negotiation: the STUDENT is the designated initiator ("impolite" side — only
// they send offers). The teacher is "polite": on offer collision the polite
// side rolls back. This kills the offer/answer glare that previously froze the
// call when both people clicked "Join" at the same moment.

export const MODES = {
  low: {
    video: { width: { ideal: 320 }, height: { ideal: 240 }, frameRate: { ideal: 10, max: 15 } },
    encodings: [{ maxBitrate: 120_000, maxFramerate: 12, scaleResolutionDownBy: 3 }],
    label: "Save data (2G)",
  },
  medium: {
    video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 15, max: 20 } },
    encodings: [{ maxBitrate: 350_000, maxFramerate: 18, scaleResolutionDownBy: 1.5 }],
    label: "Balanced (3G)",
  },
  high: {
    video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30, max: 60 } },
    encodings: [
      { rid: "l", maxBitrate: 150_000, scaleResolutionDownBy: 4 },
      { rid: "m", maxBitrate: 350_000, scaleResolutionDownBy: 2 },
      { rid: "h", maxBitrate: 1_000_000 },
    ],
    label: "Full quality (4G/Wi-Fi)",
  },
};

export async function getUserMedia(mode = "medium", audioOnly = false) {
  const preset = MODES[mode] || MODES.medium;
  const constraints = {
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    video: audioOnly ? false : preset.video,
  };
  // Older phones on low-end Android 6 may not support 720p: drop back gracefully.
  try {
    return await navigator.mediaDevices.getUserMedia(constraints);
  } catch (e) {
    if (!audioOnly) return navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    throw e;
  }
}

export async function fetchIceServers() {
  const { api } = await import("../api/client");
  try {
    const { data } = await api.get("/api/v1/tutoring/ice/");
    return data.iceServers || [{ urls: "stun:stun.l.google.com:19302" }];
  } catch {
    return [{ urls: "stun:stun.l.google.com:19302" }];
  }
}

export class PeerSession {
  constructor({ signal, iceServers, onRemoteStream, mode = "medium", isPolite = false }) {
    this.signal = signal;
    this.mode = mode;
    this.isPolite = isPolite; // teacher = true; student (initiator) = false
    this.onRemoteStream = onRemoteStream;

    this.makingOffer = false;   // an offer is in flight locally
    this.ignoreOffer = false;   // colliding offer from the impolite side
    this.remoteDesc = false;    // have we applied a remote description yet?
    this.pendingIce = [];       // ICE gathered before the remote description
    this.closed = false;

    this.pc = new RTCPeerConnection({ iceServers });
    this.localStream = null;

    this.pc.onicecandidate = (e) => {
      if (!e.candidate) return;
      if (this.remoteDesc) this.signal.send({ type: "ice", payload: { candidate: e.candidate } });
      else this.pendingIce.push(e.candidate);
    };

    // Only the student drives negotiation — the teacher waits for the offer.
    this.pc.onnegotiationneeded = () => {
      if (!this.isPolite) this.makeOffer().catch(() => {});
    };

    this.pc.ontrack = (e) => {
      const el = new MediaStream([e.track]);
      this.remoteStream = el;
      if (this.onRemoteStream) this.onRemoteStream(el);
    };
  }

  async startLocal({ audioOnly = false } = {}) {
    this.localStream = await getUserMedia(this.mode, audioOnly);
    for (const track of this.localStream.getTracks()) {
      const transceiver = this.pc.addTransceiver(track, { streams: [this.localStream] });
      this._applyEncodings(transceiver); // set bitrate caps for the current mode
    }
    return this.localStream;
  }

  // Drive negotiation as the student/initiator. Safe to call repeatedly.
  async makeOffer() {
    if (this.closed || this.makingOffer || !this.localStream) return;
    if (this.isPolite) return; // never the polite side's job
    try {
      this.makingOffer = true;
      await this.pc.setLocalDescription();
      this.signal.send({ type: "offer", payload: { sdp: this.pc.localDescription } });
    } catch (e) {
      // ROLLBACK-UNSUPPORTED on some Android builds; retry via setLocalDescription().
      try {
        await this.pc.setLocalDescription();
        this.signal.send({ type: "offer", payload: { sdp: this.pc.localDescription } });
      } catch {
        /* give up quietly; the watchdog in CallPage will recreate the peer */
      }
    } finally {
      this.makingOffer = false;
    }
  }

  // Handle any message the signaling relay delivers.
  async handleSignal(msg) {
    if (this.closed) return;
    if (msg.type === "offer" && msg.payload?.sdp) {
      await this._onRemoteOffer(msg.payload.sdp);
    } else if (msg.type === "answer" && msg.payload?.sdp) {
      if (!this._politeCheck()) return;
      await this._setRemote(msg.payload.sdp).catch(() => {});
    } else if (msg.type === "ice" && msg.payload?.candidate) {
      await this._addIce(msg.payload.candidate);
    }
  }

  // Perfect negotiation: the impolite (student) side yields on collision.
  async _onRemoteOffer(sdp) {
    this.ignoreOffer = false;
    if (this.makingOffer || this.pc.signalingState !== "stable") {
      // Collision. Polite side rolls back; impolite side ignores + keeps its own offer.
      if (this.isPolite) {
        await this.pc.setLocalDescription({ type: "rollback" }).catch(() => {});
        this.makingOffer = false;
      } else {
        this.ignoreOffer = true;
        this.makingOffer = false;
      }
    }
    if (this.ignoreOffer) return;
    try {
      await this._setRemote(sdp);
      await this.pc.setLocalDescription();
      this.signal.send({ type: "answer", payload: { sdp: this.pc.localDescription } });
    } catch (e) {
      // The collision raced us: roll back and, as the impolite side, re-offer.
      if (!this.isPolite && this.pc.signalingState !== "stable") {
        await this.pc.setLocalDescription({ type: "rollback" }).catch(() => {});
      }
      this.makeOffer().catch(() => {});
    }
  }

  async _setRemote(sdp) {
    await this.pc.setRemoteDescription(new RTCSessionDescription(sdp));
    this.remoteDesc = true;
    for (const c of this.pendingIce.splice(0)) {
      await this.pc.addIceCandidate(c).catch(() => {});
    }
  }

  async _addIce(candidate) {
    if (!this.remoteDesc) {
      this.pendingIce.push(new RTCIceCandidate(candidate));
      return;
    }
    try {
      await this.pc.addIceCandidate(new RTCIceCandidate(candidate));
    } catch {
      /* ICE races; ignore late candidates */
    }
  }

  // Guard against acting on answers/offers for a peer that moved on.
  _politeCheck() {
    if (this.pc.signalingState !== "have-local-offer" && !this.remoteDesc) return false;
    return true;
  }

  isLive() {
    return this.pc.connectionState === "connected";
  }

  // Set/update send encodings live when the mediaserver asks us to drop quality.
  applyMode(mode) {
    this.mode = mode;
    for (const tx of this.pc.getTransceivers()) {
      if (tx.sender && tx.sender.track && tx.sender.track.kind === "video") {
        this._applyEncodings(tx);
      }
    }
  }

  _applyEncodings(transceiver) {
    const preset = MODES[this.mode] || MODES.medium;
    const params = transceiver.sender.getParameters();
    if (!params.encodings) params.encodings = [];
    if (this.mode === "high" && preset.encodings.length > 1) {
      params.encodings = preset.encodings;
    } else {
      params.encodings = [{ maxBitrate: preset.encodings[0].maxBitrate }];
    }
    try {
      transceiver.sender.setParameters(params);
    } catch {
      /* Firefox may not honour all caps; fine. */
    }
  }

  close() {
    this.closed = true;
    if (this.localStream) this.localStream.getTracks().forEach((t) => t.stop());
    if (this.pc) this.pc.close();
  }
}