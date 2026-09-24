import React, { useSyncExternalStore } from "react";
import { getTheme, toggleTheme, subscribe } from "../theme";

export default function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, getTheme);
  return (
    <button
      className="icon-btn"
      onClick={toggleTheme}
      title={theme === "dark" ? "Switch to light" : "Switch to dark"}
      aria-label="Toggle theme"
    >
      {theme === "dark" ? "☀️" : "🌙"}
    </button>
  );
}
