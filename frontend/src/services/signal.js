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
    this.closed = false;
  }

  // Persistent connection: on a cold-started server (or flaky mobile network)
  // the first socket may fail mid-handshake. Keep retrying with backoff and
  // only resolve once we genuinely have an open, authenticated socket.
  connect() {
    return new Promise((resolve, reject) => {
      let settled = false;
      const done = (fn, val) => {
        if (!settled) {
          settled = true;
          fn(val);
        }
      };
      const attempt = (delay) => {
        if (this.closed) return done(reject, new Error("closed"));
        setTimeout(() => {
          if (this.closed) return done(reject, new Error("closed"));
          let ws;
          try {
            ws = new WebSocket(this.url);
          } catch {
            return done(reject, new Error("bad url"));
          }
          this.ws = ws;
          ws.onopen = () => {
            this.connected = true;
            // Replay anything we sent before the socket was up (retransmit design).
            const replay = this.queued;
            this.queued = [];
            for (const m of replay) ws.send(JSON.stringify(m));
            done(resolve);
          };
          ws.onmessage = (e) => {
            try {
              this.onMessage(JSON.parse(e.data));
            } catch {
              /* ignore malformed frames */
            }
          };
          ws.onclose = () => {
            this.connected = false;
            if (!this.closed) attempt(Math.min(2000, Math.max(800, delay * 2)));
          };
          ws.onerror = () => {
            /* onclose follows; don't reject here so cold starts retry */
          };
        }, delay);
      };
      attempt(300);
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
    this.closed = true;
    this.connected = false;
    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        /* already closed */
      }
    }
    this.ws = null;
  }
}