// api/client.js — authed fetch against the Django REST API with token refresh.
// Kept dependency-free so the bundle stays small on 2G.
//
// Base URL resolution:
//   web    -> same origin (the Django app serves the SPA, so /api is local)
//   native -> VITE_API_URL, e.g. https://taza-gojo-edu.fly.dev
//             (a native app is never "same origin", so it must be explicit)

const BASE =
  (import.meta.env.VITE_API_URL || "").replace(/\/$/, "") ||
  (typeof location !== "undefined" ? location.origin : "");

let access = localStorage.getItem("tg_access") || "";
let refresh = localStorage.getItem("tg_refresh") || "";

export function setTokens(a, r) {
  access = a || "";
  refresh = r || "";
  if (a) localStorage.setItem("tg_access", a);
  else localStorage.removeItem("tg_access");
  if (r) localStorage.setItem("tg_refresh", r);
  else localStorage.removeItem("tg_refresh");
}

export function isAuthed() {
  return Boolean(access);
}

export function getAccessToken() {
  return access;
}

async function raw(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  if (access) headers.Authorization = `Bearer ${access}`;
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  return res;
}

async function authedFetch(method, path, body, retried = false) {
  let res = await raw(method, path, body);
  if (res.status === 401 && refresh && !retried) {
    // Refresh once, then replay the request.
    const ok = await tryRefresh();
    if (ok) res = await raw(method, path, body);
  }
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok && res.status === 401 && !retried) {
    throw new ApiError(data?.detail || "Not authorised", res.status);
  }
  return { status: res.status, data };
}

async function tryRefresh() {
  if (!refresh) return false;
  try {
    const res = await fetch(`${BASE}/api/v1/auth/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) {
      setTokens("", "");
      return false;
    }
    const d = await res.json();
    setTokens(d.access, d.refresh || refresh);
    return true;
  } catch {
    return false;
  }
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export const api = {
  get: (p) => authedFetch("GET", p),
  post: (p, b) => authedFetch("POST", p, b),
  patch: (p, b) => authedFetch("PATCH", p, b),
  put: (p, b) => authedFetch("PUT", p, b),
  del: (p) => authedFetch("DELETE", p),
};

export async function login(username, password) {
  const res = await raw("POST", "/api/v1/auth/token/", { username, password });
  if (!res.ok) throw new ApiError("Wrong username or password", res.status);
  const d = await res.json();
  setTokens(d.access, d.refresh);
  return d;
}

export async function register(payload) {
  const res = await fetch(`${BASE}/api/v1/auth/register/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new ApiError(JSON.stringify(data), res.status);
  return data;
}