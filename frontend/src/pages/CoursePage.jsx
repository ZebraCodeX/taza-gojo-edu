// pages/CoursePage.jsx — Udemy-style course landing: hero header, "what you'll
// learn" list, and an accordion curriculum with progress. Visiting a lesson
// caches it (Cache-First SW) so it plays later without connectivity.

import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useStore } from "../store/app";
import { local } from "../services/offline";

export default function CoursePage() {
  const { slug } = useParams();
  const online = useStore((s) => s.online);
  const [catalog, setCatalog] = useState([]);
  const [meta, setMeta] = useState(null);
  const [open, setOpen] = useState(null);
  const [doneLessons, setDoneLessons] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      if (online) {
        try {
          const { data: list } = await api.get("/api/v1/courses/");
          const c = (Array.isArray(list) ? list : list.results || []).find((x) => x.slug === slug);
          if (c) setMeta(c);
        } catch { /* meta is decorative */ }
      }
      try {
        const { data } = await api.get(`/api/v1/courses/${slug}/`);
        setCatalog(Array.isArray(data) ? data : []);
        if (Array.isArray(data) && data[0]) setOpen(data[0].id);
      } catch {
        setErr("No cached lessons yet — connect once to download this course.");
      }
      const cached = await local.all("lessons");
      setDoneLessons(cached.map((r) => r.id));
    })();
  }, [slug, online]);

  const totalLessons = catalog.reduce((n, m) => n + (m.lessons?.length || 0), 0);
  const totalXp = catalog.reduce((n, m) => n + (m.lessons || []).reduce((x, l) => x + (l.xp || 0), 0), 0);
  const doneCount = catalog.reduce(
    (n, m) => n + (m.lessons || []).filter((l) => doneLessons.includes(l.id)).length,
    0
  );
  const pct = totalLessons ? Math.round((doneCount / totalLessons) * 100) : 0;

  return (
    <div className="course-page">
      <section className="course-head" style={{ background: meta?.color || "#3b5bdb" }}>
        <div className="course-head-in">
          <span className="badge">{meta?.icon || "🎓"} {slug}</span>
          <h1>{meta?.name || slug}</h1>
          <p>{meta?.description || "Game-based lessons, quizzes and offline play."}</p>
          <div className="meta-pills" style={{ marginTop: 8 }}>
            <span className="pill">{totalLessons} lessons</span>
            <span className="pill">+{totalXp} XP</span>
            <span className="pill">plays offline</span>
          </div>
          <div className="progress-wrap">
            <div className="progress">
              <div className="progress-bar" style={{ width: `${pct}%` }} />
            </div>
            <span className="muted" style={{ color: "#dfe7ff" }}>{pct}% complete · {doneCount}/{totalLessons} done</span>
          </div>
        </div>
      </section>

      <section className="card learn-list">
        <h2>What you'll learn</h2>
        <ul>
          <li>Follow a step-by-step curriculum written for your grade.</li>
          <li>Play game-based lessons and quizzes that test what you know.</li>
          <li>Earn XP and points with your streaks.</li>
          <li>Keep your progress — it syncs when you reconnect.</li>
        </ul>
      </section>

      {err && <p className="error">{err}</p>}

      <section>
        <h2>Curriculum</h2>
        {catalog.map((mod) => {
          const modDone = (mod.lessons || []).filter((l) => doneLessons.includes(l.id)).length;
          const isOpen = open === mod.id;
          return (
            <div className="card accordion" key={mod.id}>
              <button className="accordion-head" onClick={() => setOpen(isOpen ? null : mod.id)}>
                <span className="acc-icon">{isOpen ? "▾" : "▸"}</span>
                <span className="acc-title">{mod.title}</span>
                <span className="pill">{modDone} done</span>
              </button>
              {isOpen && (
                <div className="lessons">
                  {(mod.lessons || []).map((l) => {
                    const isDone = doneLessons.includes(l.id);
                    return (
                      <Link to={`/lesson/${l.id}`} key={l.id} className={`card lesson ${isDone ? "done" : ""}`}>
                        <div className="row between">
                          <strong>{isDone ? "✅" : "▶"} {l.title}</strong>
                          <span className="muted small">+{l.xp} XP</span>
                        </div>
                        <div className="row">
                          <span className="badge">{l.kind}</span>
                          <span className="muted small">{l.duration_minutes} min · offline-ready</span>
                        </div>
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
        {catalog.length === 0 && !err && <p className="muted small">Loading…</p>}
      </section>
    </div>
  );
}