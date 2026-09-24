// pages/TvPage.jsx — classroom / projector display.
//
// Full-screen, no chrome: a class can point a projector or smart TV at /#/tv
// and students join on their own phones. Shows the clock, the next live class,
// the join address and a rotating study prompt.

import React, { useEffect, useState } from "react";
import { api } from "../api/client";

const TIPS = [
  "Speed = distance ÷ time",
  "V = I × R  (Ohm's law)",
  "F = m × a  (Newton's second law)",
  "Energy cannot be created or destroyed — only transferred.",
  "1/2 = 2/4 = 50%",
  "A variable is a labelled box that stores a value.",
  "Series: one path. Parallel: many paths.",
  "Photosynthesis turns light into chemical energy.",
];

export default function TvPage() {
  const [now, setNow] = useState(new Date());
  const [next, setNext] = useState(null);
  const [tip, setTip] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    const r = setInterval(() => setTip((i) => (i + 1) % TIPS.length), 6000);
    return () => { clearInterval(t); clearInterval(r); };
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/api/v1/live/classes/");
        const rows = Array.isArray(data) ? data : data.results || [];
        const upcoming = rows
          .filter((c) => c.status === "live" || new Date(c.scheduled_at) >= new Date(Date.now() - 3600e3))
          .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at));
        setNext(upcoming[0] || null);
      } catch { /* offline is fine — the clock and tips still work */ }
    })();
  }, []);

  const joinUrl = typeof window !== "undefined" ? `${location.origin}/#/dashboard` : "";
  const clock = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const date = now.toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" });

  return (
    <div className="tv">
      <div className="tv-top">
        <div className="tv-brand">
          <span className="brand-mark lg">Tz</span>
          <span>Taza-Gojo <b>School</b></span>
        </div>
        <div className="tv-clock">
          <div className="tv-time">{clock}</div>
          <div className="tv-date">{date}</div>
        </div>
      </div>

      <div className="tv-main">
        {next ? (
          <div className="tv-class">
            <div className="tv-class-tag">{next.status === "live" ? "🔴 LIVE NOW" : "NEXT CLASS"}</div>
            <h1>{next.title}</h1>
            <p className="tv-class-meta">
              {next.subject} · {new Date(next.scheduled_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} · {next.duration_minutes} min
            </p>
          </div>
        ) : (
          <div className="tv-class">
            <h1>Learn anything. Anywhere.</h1>
            <p className="tv-class-meta">Cambridge/IGCSE-aligned lessons, adaptive tests, labs and live classes.</p>
          </div>
        )}

        <div className="tv-join">
          <div className="tv-join-label">Join from your phone</div>
          <div className="tv-join-url">{joinUrl}</div>
          <div className="tv-join-hint">Open the link · sign in · start learning</div>
        </div>
      </div>

      <div className="tv-tip">
        <span className="tv-tip-label">💡 Remember</span>
        <span className="tv-tip-text">{TIPS[tip]}</span>
      </div>

      <a className="tv-exit" href="#/dashboard">Exit display</a>
    </div>
  );
}
