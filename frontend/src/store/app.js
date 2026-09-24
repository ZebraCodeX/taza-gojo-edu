// store/app.js — tiny global store (no external state lib) + a hook.

import { useSyncExternalStore } from "react";

let state = {
  user: null, // profile payload
  online: navigator.onLine,
  mode: "high", // video quality preset
  points: 0,
};

const listeners = new Set();

function set(partial) {
  state = { ...state, ...(typeof partial === "function" ? partial(state) : partial) };
  listeners.forEach((l) => l());
}

export const store = {
  get: () => state,
  set,
  subscribe: (fn) => {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
};

export function useStore(selector) {
  const value = useSyncExternalStore(store.subscribe, () => selector(state));
  return value;
}

window.addEventListener("online", () => set({ online: true }));
window.addEventListener("offline", () => set({ online: false }));