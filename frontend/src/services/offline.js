// services/offline.js — IndexedDB-backed offline lesson store + sync queue.
//
// Every completed action is written locally FIRST (the child on 2G shouldn't
// wait on the network), and flushed to the Django backend in batches when the
// connection returns. Content lessons are cached Cache-First by the SW; this
// module handles *progress* and *conversation* writes.

const DB = "taza_gojo";
const VER = 2;

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, VER);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("keys")) db.createObjectStore("keys");
      if (!db.objectStoreNames.contains("queue")) db.createObjectStore("queue", { keyPath: "id" });
      if (!db.objectStoreNames.contains("lessons")) db.createObjectStore("lessons", { keyPath: "id" });
      if (!db.objectStoreNames.contains("materials")) db.createObjectStore("materials", { keyPath: "id" });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function tx(store, mode, fn) {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const t = db.transaction(store, mode);
    const s = t.objectStore(store);
    const out = fn(s);
    t.oncomplete = () => resolve(out.result !== undefined ? out.result : out);
    t.onerror = () => reject(t.error);
  });
}

export const local = {
  put: (store, val) => tx(store, "readwrite", (s) => s.put(val)),
  get: (store, key) => tx(store, "readonly", (s) => s.get(key)),
  del: (store, key) => tx(store, "readwrite", (s) => s.delete(key)),
  all: (store) =>
    tx(store, "readonly", (s) => {
      const all = s.getAll();
      return all;
    }),
};

let deviceId =
  localStorage.getItem("tg_device") ||
  (() => {
    const id = "d" + Math.random().toString(36).slice(2, 10);
    localStorage.setItem("tg_device", id);
    return id;
  })();

// Enqueue an offline action; returns immediately.
export function enqueue(op) {
  const id = (op.id && op.id.startsWith("op-")) ? op.id : "op-" + crypto.randomUUID().slice(0, 12);
  return local.put("queue", { id, op, at: Date.now() });
}

async function flush() {
  const rows = await local.all("queue");
  if (!rows.length) return;
  const { api } = await import("../api/client");
  try {
    const { data } = await api.post("/api/v1/offline/sync/", {
      device_id: deviceId,
      ops: rows.map((r) => ({ id: r.id, ...r.op })),
    });
    for (const r of rows) await local.del("queue", r.id);
    return data;
  } catch {
    return { pending: rows.length };
  }
}

export async function syncNow() {
  return flush();
}

// True when running inside a Capacitor/Android/iOS webview (native shell),
// where service workers are unsupported/no use and "online" means the device.
export function isNative() {
  return typeof window !== "undefined" && !!(window.Capacitor && window.Capacitor.isNativePlatform);
}

export function registerServiceWorker() {
  if (isNative() || !navigator.serviceWorker) {
    // Native shell: no SW needed; still flush the queue on 'online'.
    window.addEventListener("online", () => flush());
    return;
  }
  navigator.serviceWorker.register("/sw.js").catch(() => {});
  navigator.serviceWorker.addEventListener("message", (e) => {
    if (e.data?.type === "TAZAGOJO_FLUSH_QUEUE") flush();
  });
  // Flush whenever we come back online (also covers the first page load).
  window.addEventListener("online", () => flush());
  if (navigator.onLine) setTimeout(flush, 1500);
}

// Progress shorthand used by pages + the game renderer.
export async function reportProgress(lessonId, { completed = true, score = 0, stars = 0 }) {
  await enqueue({ op: "progress", data: { lesson: Number(lessonId), completed, score, stars } });
  // Best-effort immediate sync when online; the queue guarantees delivery.
  if (navigator.onLine) flush();
}

/* ----------------------- downloadable library cache ----------------------- */

export const materialStore = {
  // Save a material (bookmark or full content) for offline reading.
  async save(id, record) {
    await local.put("materials", { id: Number(id), savedAt: Date.now(), ...record });
  },
  async get(id) {
    return local.get("materials", Number(id));
  },
  async all() {
    return local.all("materials");
  },
  async remove(id) {
    return local.del("materials", Number(id));
  },
};

// Download a material's full body so it can be read with zero signal:
//   links-only materials are saved as bookmarks; content-bearing ones fetch the
//   detail (HTML/notes) and store it. Progress-tracks it as an offline op so
//   the server-side download stat is updated even when saved while offline.
export async function downloadMaterial(material, { api } = {}) {
  let record = material;
  if (material.downloadable) {
    try {
      const { data } = await api.get(`/api/v1/library/materials/${material.id}/`);
      record = data;
    } catch {
      record = material; // offline: bookmark with what the list had
    }
  }
  await materialStore.save(material.id, record);
  await enqueue({ op: "material", data: { id: material.id } });
  if (navigator.onLine) flush();
  return record;
}