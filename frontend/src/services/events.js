// services/events.js — offline-first learning analytics.
//
// Events are buffered in localStorage (cheap, synchronous, survives reloads)
// and flushed to /api/v1/analytics/events/ when online. Nothing here blocks
// learning: if the flush fails the events simply stay queued.

const KEY = "tg_events";
const MAX = 300;

function read() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

function write(rows) {
  try {
    localStorage.setItem(KEY, JSON.stringify(rows.slice(-MAX)));
  } catch { /* storage full / private mode — drop silently */ }
}

export function track(kind, data = {}) {
  const rows = read();
  rows.push({
    kind,
    subject: data.subject || "",
    object_type: data.object_type || "",
    object_id: data.object_id || null,
    value: data.value || 0,
    metadata: data.metadata || {},
    client_ts: new Date().toISOString(),
  });
  write(rows);
  if (navigator.onLine) flush();
}

export async function flush() {
  const rows = read();
  if (!rows.length) return;
  try {
    const { api } = await import("../api/client");
    await api.post("/api/v1/analytics/events/", { events: rows });
    write([]);
  } catch {
    /* stay queued */
  }
}

if (typeof window !== "undefined") {
  window.addEventListener("online", flush);
}
