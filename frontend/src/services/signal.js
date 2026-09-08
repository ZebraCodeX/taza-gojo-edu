// services/signal.js — WebRTC signaling over the Django Channels WebSocket.
//
// The browser never talks to the peer directly for signaling; everything goes
// through our relay so SDP/ICE survive flaky NAT and spotty mobile networks.
//
// Resilience:
//   * persistent connection with backoff (cold-started servers, flaky mast)
//   * queued sends are replayed once a socket is genuinely open
//   * if the server rejects auth (expired JWT), we refresh the token on the
//     spot and reconnect with the new one instead of retrying in a loop.

import { refreshAccessToken } from "../api/client";

export class SignalClient {
  constructor({ sessionId, token, getToken, onMessage }) {
    this.sessionId = sessionId;
    this.token = token;
    this.getToken = getToken; // optional: () => latest access token
    this.onMessage = onMessage;
    this.queued = [];
    this.ws = null;
    this.connected = false;
    this.closed = false;
  }

  _url() {
    const apiUrl = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "") || location.origin;
    const wsProto = apiUrl.startsWith("https:") ? "wss" : "ws";
    const tok = this.getToken ? this.getToken() : this.token;
    return `${wsProto}://${apiUrl.replace(/^https?:\/\//, "")}/ws/tutor/${this.sessionId}/?device=web&token=${encodeURIComponent(tok)}`;
  }

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
        setTimeout(async () => {
          if (this.closed) return done(reject, new Error("closed"));
          let ws;
          try {
            ws = new WebSocket(this._url());
          } catch {
            return done(reject, new Error("bad url"));
          }
          this.ws = ws;
          ws.onopen = () => {
            this.connected = true;
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
          ws.onclose = async (e) => {
            this.connected = false;
            if (this.closed) return;
            if (e.code === 4001 || e.code === 4401 || e.code === 4003) {
              // Auth rejected — the JWT likely expired. Refresh once, then retry.
              try {
                const ok = await refreshAccessToken();
                if (ok) this.token = this.getToken ? this.getToken() : this.token;
              } catch {
                /* offline: keep the stale token; retry anyway */
              }
            }
            const next = Math.min(2000, Math.max(800, delay * 2));
            attempt(next);
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