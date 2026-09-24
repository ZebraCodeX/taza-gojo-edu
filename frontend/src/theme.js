// theme.js — light/dark theme, remembered per device, defaults to the OS.
const KEY = "tg_theme";
const listeners = new Set();

export function getTheme() {
  const stored = localStorage.getItem(KEY);
  if (stored === "light" || stored === "dark") return stored;
  return typeof matchMedia !== "undefined" && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", theme === "dark" ? "#0b1020" : "#6d28d9");
}

export function setTheme(theme) {
  localStorage.setItem(KEY, theme);
  applyTheme(theme);
  listeners.forEach((l) => l());
}

export function toggleTheme() {
  setTheme(getTheme() === "dark" ? "light" : "dark");
}

export function initTheme() {
  applyTheme(getTheme());
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
