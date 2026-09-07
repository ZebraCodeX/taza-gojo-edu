# Taza-Gojo EDU — offline-first design

Most homes on the target networks see 2G (≈10–30 KB/s) or intermittent 3G. The
rule everywhere in the app is **write locally first, flush later**.

## Layers

1. **App shell (service worker, `public/sw.js`)**
   - Cache-First for `/`, `/index.html`, `/assets/*` → the app boots with **no**
     network round trips.
   - Network-First for GET `/api/*` → a lesson you opened once still opens later
     without a signal (the fresh reply is cached on each read).
   - One cache per version (`tazagojo-shell-v1`, `tazagojo-data-v1`), old caches pruned
     on activate, `skipWaiting`+`clients.claim` so an updated SW takes over fast.

2. **Lesson data (IndexedDB `lessons` store)**
   `LessonPage` reads cached copy instantly, then updates it from the network.
   This means the *content* needed to play a game is never blocked on the network;
   only freshness is.

3. **Offline action queue (`services/offline.js`)**
   Every state-changing action is written to the `queue` object store first:
   ```js
   await enqueue({ op: "progress", data: { lesson: 4, completed: true, score: 80, stars: 2 } });
   await enqueue({ op: "conversation", data: { ... } });
   ```
   - `syncNow()` / the `online` event / a background-sync message batch-flushes
     the queue to `POST /api/v1/offline/sync/`.
   - The server applies each op **exactly once** via a `(device_id, op_id)`
     uniqueness log (`offline.SyncBatch`), so retries are safe.
   - Backend ops supported today: `progress`, `conversation`; the view is a
     registry (`offline/views.py`) so new op types are one line each.

4. **UI affordances**
   - Dashboard shows an `Online` / `Offline — progress saved` pill.
   - Lesson completion works fully offline; stars show immediately from the
     local queue.

## Bandwidth budgets (calibrated for 2G–3G)

| Asset | Size | Notes |
|---|---|---|
| App shell (CSS+JS, gzipped) | ~66 KB | lazy-launched page chunks add a few KB |
| One game lesson JSON | 2–8 KB | agents author these |
| Progress sync batch | ~100 B/op | batched in one POST |
| Video call, low mode | ~120 kbps | 320×240 @ 10fps, audio-first (2G) |
| Video call, medium | ~350 kbps | 480p @ 15–18fps (3G) |

## Pre-seeding content for schools without internet

The `manifest` endpoint (`/api/v1/offline/manifest/`) enumerates all courses and
lessons. A school facilitator on any device with once-weekly internet can load
each lesson once — it lands in the SW data cache + IndexedDB — or the same JSON
can be dropped on a flash drive / local Wi-Fi AP and loaded from `file://`. After
that the classroom runs for weeks on LAN alone while sync catches up whenever a
signal appears.

## Testing notes

- API sync semantics are tested in `backend/apps/offline/tests.py` minimal set —
  the two invariants to preserve: **idempotency** (replayed batch ⇒ no dupes) and
  **ordering** (a batch applies in submission order).
- The SW cannot be unit-tested in Node; keep it tiny and review the two branches
  (`isShell` / `isApi`) by hand. It is intentionally not framework-heavy.