// pages/DashboardPage.jsx — the learning home.
// One place that answers: what should I do next, what's coming up, and how am
// I doing? Everything degrades gracefully offline (cached data + IndexedDB).

import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { store, useStore } from "../store/app";
import { local } from "../services/offline";
import { useI18n } from "../i18n";

const SUBJECT_ICON = { math: "🧮", english: "📖", science: "🔬", computing: "💻", physics: "🧲", electricity: "⚡" };

const QUICK = [
  { to: "/assessments", icon: "📝", title: "Assessments", sub: "Tests with instant feedback" },
  { to: "/labs", icon: "🧪", title: "Labs", sub: "Coding, circuits & science" },
  { to: "/live", icon: "🎥", title: "Live classes", sub: "1:1 and groups up to 15" },
  { to: "/progress", icon: "📈", title: "Progress", sub: "Your learning this month" },
];

export default function DashboardPage() {
  const { t } = useI18n();
  const online = useStore((s) => s.online);
  const user = useStore((s) => s.user);
  const points = useStore((s) => s.points);
  const [courses, setCourses] = useState([]);
  const [classes, setClasses] = useState([]);
  const [assessments, setAssessments] = useState([]);
  const [labs, setLabs] = useState([]);
  const [recent, setRecent] = useState([]);
  const [certs, setCerts] = useState(0);
  const [summary, setSummary] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (user?.onboarded === false) location.hash = "#/profile";
  }, [user]);

  useEffect(() => {
    (async () => {
      const get = (url) => api.get(url).then((r) => (Array.isArray(r.data) ? r.data : r.data?.results || [])).catch(() => null);
      const [c, lc, as, lb, ce, su] = await Promise.all([
        get("/api/v1/courses/"),
        get("/api/v1/live/classes/"),
        get("/api/v1/assessment/assessments/"),
        get("/api/v1/labs/labs/"),
        get("/api/v1/assessment/certificates/"),
        api.get("/api/v1/analytics/events/summary/").then((r) => r.data).catch(() => null),
      ]);
      if (c) setCourses(c); else setErr("Offline — showing saved content.");
      if (lc) setClasses(lc.slice(0, 3));
      if (as) setAssessments(as.slice(0, 4));
      if (lb) setLabs(lb.slice(0, 4));
      if (ce) setCerts(ce.length);
      if (su) setSummary(su);

      const cached = await local.all("lessons");
      setRecent(cached.slice(-4).reverse());
    })();
  }, []);

  const firstName = user?.user?.username || "learner";
  const grade = user?.grade_level ? ` · Grade ${user.grade_level}` : "";
  const goals = user?.goals || [];
  const streak = user?.streak_days || 0;

  return (
    <div className="home">
      <section className="hero">
        <div>
          <h1>Welcome back, {firstName} 👋</h1>
          <p className="hero-sub">
            Your school, online. Pick up a lesson, practise with a test, run a lab,
            or join a live class — everything works offline once it's saved.
          </p>
          <div className="row">
            <Link className="btn primary" to={recent[0] ? `/lesson/${recent[0].id}` : "/library"}>
              {recent[0] ? "▶ Continue learning" : "📚 Browse resources"}
            </Link>
            <Link className="btn ghost" to="/live">🎥 Live classes</Link>
          </div>
        </div>
        <div className="hero-art">🎓</div>
      </section>

      <div className="stat-cards">
        <div className="stat-card"><span className="sc-ico">⚡</span><span><span className="sc-num">{points}</span><span className="sc-label">points</span></span></div>
        <div className="stat-card"><span className="sc-ico">🔥</span><span><span className="sc-num">{streak}</span><span className="sc-label">day streak</span></span></div>
        <div className="stat-card"><span className="sc-ico">🏫</span><span><span className="sc-num">{courses.length}</span><span className="sc-label">subjects</span></span></div>
        <div className="stat-card"><span className="sc-ico">🏅</span><span><span className="sc-num">{certs}</span><span className="sc-label">{t("certificates")}</span></span></div>
      </div>

      <div className="grid quick-actions" style={{ marginTop: 14 }}>
        {QUICK.map((q) => (
          <Link key={q.to} to={q.to} className="card quick">
            <span className="quick-ico">{q.icon}</span>
            <span><b>{q.title}</b><small>{q.sub}</small></span>
          </Link>
        ))}
      </div>

      {goals.length > 0 && (
        <section className="card roadmap" style={{ marginTop: 14 }}>
          <div className="row between">
            <h2 style={{ margin: 0 }}>🗺 My learning roadmap</h2>
            <Link className="linkbtn" to="/profile">Edit →</Link>
          </div>
          <div className="roadmap-row" style={{ marginTop: 10 }}>
            {goals.map((g, i) => (
              <div className="goal-chip" key={i}>
                <span className="goal-ico">{SUBJECT_ICON[g.subject] || "🎯"}</span>
                <span className="goal-txt"><b>{g.goal}</b><small>{g.target_weeks ? `${g.target_weeks} wk` : "ongoing"}</small></span>
              </div>
            ))}
          </div>
        </section>
      )}

      {classes.length > 0 && (
        <section>
          <div className="section-head">
            <h2>🎥 Upcoming classes</h2>
            <Link className="linkbtn" to="/live">All classes →</Link>
          </div>
          <div className="list">
            {classes.map((c) => (
              <Link key={c.id} to="/live" className="list-row">
                <span className="lr-ico">{SUBJECT_ICON[c.subject] || "🎥"}</span>
                <span className="lr-main">
                  <span className="lr-title">{c.title}</span>
                  <span className="lr-sub">{new Date(c.scheduled_at).toLocaleString()} · {c.duration_minutes} min · {c.attendee_count}/{c.max_participants}</span>
                </span>
                <span className={"pill" + (c.status === "live" ? " live" : "")}>{c.status}</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section>
        <div className="section-head">
          <h2>Core subjects{grade}</h2>
          <span className="muted small">game-based · offline-ready</span>
        </div>
        {err && <p className="error small">{err}</p>}
        <div className="grid courses">
          {courses.map((c) => (
            <Link to={`/course/${c.slug}`} key={c.slug} className="card course">
              <div className="course-thumb" style={{ background: c.color }}>
                <span>{c.icon}</span>
              </div>
              <h3>{c.name}</h3>
              <p className="muted small">{c.description}</p>
              <span className="tag">{c.slug}</span>
            </Link>
          ))}
          {courses.length === 0 && online && <p className="muted">Courses will appear here once you connect.</p>}
        </div>
      </section>

      {recent.length > 0 && (
        <section>
          <div className="section-head"><h2>⏱ Continue learning</h2></div>
          <div className="list">
            {recent.map((l) => (
              <Link key={l.id} to={`/lesson/${l.id}`} className="list-row">
                <span className="lr-ico">▶</span>
                <span className="lr-main">
                  <span className="lr-title">{l.title}</span>
                  <span className="lr-sub">{l.kind} · saved on this device</span>
                </span>
                <span className="muted small">+{l.xp || 0} XP</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", marginTop: 8 }}>
        <section>
          <div className="section-head"><h2>📝 Practise</h2><Link className="linkbtn" to="/assessments">All →</Link></div>
          <div className="list">
            {assessments.map((a) => (
              <Link key={a.slug} to={`/assessment/${a.slug}`} className="list-row">
                <span className="lr-ico">{SUBJECT_ICON[a.subject] || "📝"}</span>
                <span className="lr-main">
                  <span className="lr-title">{a.title}</span>
                  <span className="lr-sub">{a.kind}{a.adaptive ? " · adaptive" : ""} · pass {a.pass_score}%</span>
                </span>
              </Link>
            ))}
            {assessments.length === 0 && <p className="muted small">No assessments yet.</p>}
          </div>
        </section>

        <section>
          <div className="section-head"><h2>🧪 Labs</h2><Link className="linkbtn" to="/labs">All →</Link></div>
          <div className="list">
            {labs.map((l) => (
              <Link key={l.slug} to={`/lab/${l.slug}`} className="list-row">
                <span className="lr-ico">{SUBJECT_ICON[l.subject] || "🧪"}</span>
                <span className="lr-main">
                  <span className="lr-title">{l.title}</span>
                  <span className="lr-sub">{l.kind} · +{l.xp} XP</span>
                </span>
              </Link>
            ))}
            {labs.length === 0 && <p className="muted small">No labs yet.</p>}
          </div>
        </section>
      </div>

      {summary && (
        <section className="card" style={{ marginTop: 18 }}>
          <div className="row between">
            <h2 style={{ margin: 0 }}>📈 This month</h2>
            <Link className="linkbtn" to="/progress">Details →</Link>
          </div>
          <div className="stat-row">
            <div className="stat"><b>{summary.active_days}</b><span>active days</span></div>
            <div className="stat"><b>{Math.round((summary.watch_seconds || 0) / 60)}</b><span>min of video</span></div>
            <div className="stat"><b>{summary.total_events}</b><span>activities</span></div>
          </div>
        </section>
      )}

      <section className="card tip" style={{ marginTop: 18 }}>
        <h3>💡 Study tip</h3>
        <p className="muted">
          Watch the <b>video lecture</b> for a lesson before you play it, then take the
          matching <b>assessment</b> to lock it in. Save a <b>study pack</b> from the Library
          before class so it works with zero signal. Stuck? Book a <b>live tutor</b>.
        </p>
      </section>
    </div>
  );
}

export async function loadProfile() {
  try {
    const { data } = await api.get("/api/v1/auth/me/");
    store.set({ user: data, points: data.points });
  } catch { /* offline is fine */ }
}
