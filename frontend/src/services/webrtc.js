// services/webrtc.js — camera + mic setup with bandwidth-aware presets.
//
// The "most important part" of the app: face-to-face video with a tutor in
// another country. Everything is tuned so the call survives 2G:
//
//   low    -> 320x240 @ 10fps, ~120 kbps video (audio always preserved)
//   medium -> 640x480 @ 15fps, ~350 kbps
//   high   -> 1280x720 @ 30fps, up to 1 Mbps (only sane links)
//
// The mediaserver or the signal relay can push {"type":"mode",...} to drop
// quality live when RTCP loss climbs (see mediaserver/src/bitrate.hpp).

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
  constructor({ signal, iceServers, onRemoteStream, mode = "medium" }) {
    this.signal = signal;
    this.mode = mode;
    this.onRemoteStream = onRemoteStream;
    this.pc = new RTCPeerConnection({ iceServers });
    this.localStream = null;

    this.pc.onicecandidate = (e) => {
      if (e.candidate) this.signal.send({ type: "ice", payload: { candidate: e.candidate } });
    };
    this.pc.ontrack = (e) => {
      const el = new MediaStream([e.track]);
      this.remoteStream = el;
      if (this.onRemoteStream) this.onRemoteStream(el);
    };
    this.pc.onconnectionstatechange = () => {
      if (this.pc.connectionState === "connected" || this.pc.connectionState === "connecting") {
        // keep a beacon through signaling so both sides know it's alive
      }
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
      // Simulcast: give the SFU layers to pick from.
      params.encodings = preset.encodings;
    } else {
      // Single encoding, capped.
      params.encodings = [{ maxBitrate: preset.encodings[0].maxBitrate }];
    }
    try {
      transceiver.sender.setParameters(params);
    } catch {
      /* Firefox may not honour all caps; fine. */
    }
  }

  async makeOffer() {
    const offer = await this.pc.createOffer();
    await this.pc.setLocalDescription(offer);
    this.signal.send({ type: "offer", payload: { sdp: this.pc.localDescription } });
  }

  async acceptOffer(sdp) {
    await this.pc.setRemoteDescription(new RTCSessionDescription(sdp));
    const answer = await this.pc.createAnswer();
    await this.pc.setLocalDescription(answer);
    this.signal.send({ type: "answer", payload: { sdp: this.pc.localDescription } });
  }

  async acceptAnswer(sdp) {
    await this.pc.setRemoteDescription(new RTCSessionDescription(sdp));
  }

  async addIce(candidate) {
    try {
      await this.pc.addIceCandidate(new RTCIceCandidate(candidate));
    } catch {
      /* ICE races; ignore late candidates */
    }
  }

  close() {
    if (this.localStream) this.localStream.getTracks().forEach((t) => t.stop());
    if (this.pc) this.pc.close();
  }
}