// services/signal.js — WebRTC signaling over the Django Channels WebSocket.
//
// The browser never talks to the peer directly for signaling; everything goes
// through our relay so SDP/ICE survive flaky NAT and spotty mobile networks.

export class SignalClient {
  constructor({ sessionId, token, onMessage }) {
    const apiUrl = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "") || location.origin;
    const wsProto = apiUrl.startsWith("https:") ? "wss" : "ws";
    this.url = `${wsProto}://${apiUrl.replace(/^https?:\/\//, "")}/ws/tutor/${sessionId}/?device=web&token=${encodeURIComponent(token)}`;
    this.onMessage = onMessage;
    this.queued = [];
    this.ws = null;
    this.connected = false;
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url);
      this.ws.onopen = () => {
        this.connected = true;
        // Replay anything we sent before the socket was up (retransmit design).
        for (const m of this.queued) this.ws.send(JSON.stringify(m));
        this.queued = [];
        resolve();
      };
      this.ws.onmessage = (e) => {
        try {
          this.onMessage(JSON.parse(e.data));
        } catch {
          /* ignore malformed frames */
        }
      };
      this.ws.onclose = () => {
        this.connected = false;
        // Bad phone networks close sockets; reconnect with backoff.
        setTimeout(() => this.connect().catch(() => {}), 1500);
      };
      this.ws.onerror = () => {
        reject(new Error("signaling error"));
      };
    });
  }

  send(msg) {
    if (!this.connected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.queued.push(msg);
      return;
    }
    this.ws.send(JSON.stringify(msg));
  }

  close() {
    if (this.ws) this.ws.close();
  }
}