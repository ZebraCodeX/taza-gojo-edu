// pages/DashboardPage.jsx — the "Learn" home, Udemy-style: a hero banner, the
// core courses as course cards, a search box, and rails for your roadmap and
// saved library. Works online or from the SW/IndexedDB cache.

import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { store, useStore } from "../store/app";
import { local } from "../services/offline";

const SUBJECT_ICON = { math: "🧮", english: "📖", science: "🔬", computing: "💻" };

export default function DashboardPage() {
  const online = useStore((s) => s.online);
  const user = useStore((s) => s.user);
  const points = useStore((s) => s.points);
  const [courses, setCourses] = useState([]);
  const [materials, setMaterials] = useState([]);
  const [savedIds, setSavedIds] = useState(new Set());
  const [err, setErr] = useState("");

  useEffect(() => {
    if (user?.onboarded === false) {
      location.hash = "#/profile";
    }
  }, [user]);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/api/v1/courses/");
        setCourses(Array.isArray(data) ? data : data.results || []);
      } catch {
        setErr("Offline — showing cached lessons.");
      }
      const cached = await local.all("materials");
      const c = cached.filter((m) => m.downloadable || m.content);
      if (c.length) {
        setMaterials(c.slice(0, 8));
        setSavedIds(new Set(c.map((m) => m.id)));
      }
      try {
        const { data } = await api.get("/api/v1/library/materials/?kind=study_pack&page_size=8");
        const list = Array.isArray(data) ? data : data.results || [];
        if (list.length) setMaterials(list);
      } catch { /* honestly offline is fine */ }
    })();
  }, []);

  const firstName = (user?.user?.username || "learner");
  const grade = user?.grade_level ? ` · Grade ${user.grade_level}` : "";
  const goals = user?.goals || [];

  return (
    <div className="home">
      <section className="hero">
        <div>
          <h1>Welcome, {firstName} {points > 0 && <span className="pill heroPill">⚡ {points} points</span>}</h1>
          <p className="hero-sub">
            Learn like a school — lessons, free books, study packs and live tutors.
            Everything works offline after you save it.
          </p>
          <div className="row">
            <Link className="btn primary" to="/library">📚 Browse the library</Link>
            <Link className="btn ghost" to="/ai">💬 Ask the AI tutor</Link>
          </div>
        </div>
        <div className="hero-art">🎓</div>
      </section>

      {goals.length > 0 && (
        <section className="roadmap card">
          <div className="row between">
            <h2>🗺 My learning roadmap</h2>
            <Link className="linkbtn" to="/profile">Edit →</Link>
          </div>
          <div className="roadmap-row">
            {goals.map((g, i) => (
              <div className="goal-chip" key={i}>
                <span className="goal-ico">{SUBJECT_ICON[g.subject] || "🎯"}</span>
                <span className="goal-txt">
                  <b>{g.goal}</b>
                  <small>{g.target_weeks ? `${g.target_weeks} wk` : "ongoing"}</small>
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <div className="row between">
          <h2>Core courses{grade}</h2>
          <span className="muted small">game-based · offline-ready</span>
        </div>
        <p className="muted small">Tap a course to start a module — progress is saved even without signal.</p>
        {err && <p className="error">{err}</p>}
        <div className="grid courses">
          {courses.map((c) => (
            <Link to={`/course/${c.slug}`} key={c.slug} className="card course">
              <div className="course-thumb" style={{ background: c.color }}>
                <span className="course-icon">{c.icon}</span>
              </div>
              <h3>{c.name}</h3>
              <p className="muted small">{c.description}</p>
              <span className="tag" style={{ background: c.color }}>{c.slug}</span>
            </Link>
          ))}
          {courses.length === 0 && online && <p className="muted">Courses will appear here once you connect.</p>}
        </div>
      </section>

      <section>
        <div className="row between">
          <h2>Study materials</h2>
          <Link className="linkbtn" to="/library">All →</Link>
        </div>
        <div className="grid mats rail">
          {materials.map((m) => (
            <Link to={`/library/read/${m.id}`} key={m.id} className="card mat">
              <div className="row spinner">
                <span className="badge kind">{m.kind?.replace("_", " ")}</span>
                {m.downloadable && <span className="pill">Downloadable</span>}
              </div>
              <h3>{m.title}</h3>
              <p className="muted small">{m.subject} · {m.grade_band || (m.grade_start ? `Grade ${m.grade_start}+` : "")}</p>
            </Link>
          ))}
          {materials.length === 0 && (
            <p className="muted small">No materials saved yet. Open the Library and save your first study pack — it works offline.</p>
          )}
        </div>
      </section>

      <section className="tip card">
        <h3>💡 Study tip</h3>
        <p className="muted">
          Save a <b>study pack</b> from the Library before class — it downloads to this
          device so you can keep learning with zero signal. Ask the AI tutor anything
          from your notes; it pulls the right material for you.
        </p>
      </section>
    </div>
  );
}

export async function loadProfile() {
  try {
    const { data } = await api.get("/api/v1/auth/me/");
    store.set({ user: data, points: data.points });
  } catch { /* let the offline store stand in */ }
}