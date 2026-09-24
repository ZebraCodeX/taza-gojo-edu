// pages/TeacherPage.jsx — teacher console: class overview + grading queue.
// Teachers review essay answers (auto-graded items need no attention) and the
// attempt is finalised (and certified) the moment the last manual item is graded.

import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import Empty from "../components/Empty";

export default function TeacherPage() {
  const [overview, setOverview] = useState(null);
  const [pending, setPending] = useState([]);
  const [attempts, setAttempts] = useState([]);
  const [tab, setTab] = useState("grading");
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    const [o, p, a] = await Promise.all([
      api.get("/api/v1/assessment/attempts/overview/").then((r) => r.data).catch(() => null),
      api.get("/api/v1/assessment/attempts/pending/").then((r) => r.data).catch(() => []),
      api.get("/api/v1/assessment/attempts/").then((r) => (Array.isArray(r.data) ? r.data : r.data?.results || [])).catch(() => []),
    ]);
    if (o) setOverview(o);
    setPending(p || []);
    setAttempts((a || []).slice(0, 20));
  };

  useEffect(() => { load(); }, []);

  const grade = async (attemptId, responseId, awarded, feedback) => {
    try {
      await api.post(`/api/v1/assessment/attempts/${attemptId}/responses/${responseId}/grade/`, { awarded, feedback });
      setMsg("Graded ✓");
      await load();
    } catch {
      setErr("Could not save that grade.");
    }
  };

  return (
    <div>
      <PageHeader icon="👩🏽‍🏫" title="Teacher console" subtitle="Review work, watch progress, and finalise manual grades." />

      {overview && (
        <div className="stat-cards">
          <div className="stat-card"><span className="sc-ico">📝</span><span><span className="sc-num">{overview.attempts}</span><span className="sc-label">attempts</span></span></div>
          <div className="stat-card"><span className="sc-ico">⏳</span><span><span className="sc-num">{overview.pending_grading}</span><span className="sc-label">to grade</span></span></div>
          <div className="stat-card"><span className="sc-ico">✅</span><span><span className="sc-num">{overview.pass_rate}%</span><span className="sc-label">pass rate</span></span></div>
          <div className="stat-card"><span className="sc-ico">🏅</span><span><span className="sc-num">{overview.certificates}</span><span className="sc-label">certificates</span></span></div>
        </div>
      )}

      <div className="tabs" style={{ marginTop: 16 }}>
        <button className={`tab ${tab === "grading" ? "on" : ""}`} onClick={() => setTab("grading")}>Grading queue {pending.length > 0 && `(${pending.length})`}</button>
        <button className={`tab ${tab === "attempts" ? "on" : ""}`} onClick={() => setTab("attempts")}>Recent attempts</button>
        <button className={`tab ${tab === "live" ? "on" : ""}`} onClick={() => setTab("live")}>Live classes</button>
      </div>

      {msg && <p className="success">{msg}</p>}
      {err && <p className="error">{err}</p>}

      {tab === "grading" && (
        pending.length === 0 ? (
          <Empty icon="✅" title="Nothing to grade" text="Auto-graded items are scored instantly. Essays will appear here." />
        ) : (
          <div className="list">
            {pending.map((r) => (
              <GradeRow key={r.id} r={r} onGrade={grade} />
            ))}
          </div>
        )
      )}

      {tab === "attempts" && (
        <div className="list">
          {attempts.map((a) => (
            <div key={a.id} className="list-row" style={{ cursor: "default" }}>
              <span className="lr-ico">📝</span>
              <span className="lr-main">
                <span className="lr-title">{a.assessment_slug}</span>
                <span className="lr-sub">{new Date(a.started_at).toLocaleString()}</span>
              </span>
              <span className="pill soft">{a.status}</span>
              <span className="muted small">{a.score}/{a.max_score}</span>
            </div>
          ))}
          {attempts.length === 0 && <Empty icon="📝" title="No attempts yet" />}
        </div>
      )}

      {tab === "live" && (
        <div className="card">
          <p className="muted">Schedule and run live classes from the Live page — 1:1 or groups up to 15.</p>
          <Link className="btn primary" to="/live">Go to live classes →</Link>
        </div>
      )}
    </div>
  );
}

function GradeRow({ r, onGrade }) {
  const [awarded, setAwarded] = useState(r.max_points);
  const [feedback, setFeedback] = useState("");
  const [open, setOpen] = useState(false);
  return (
    <div className="card">
      <div className="row between">
        <div>
          <span className="badge kind">essay</span>
          <b style={{ marginLeft: 8 }}>{r.username}</b>
          <span className="muted small"> · {r.assessment}</span>
        </div>
        <button className="btn sm" onClick={() => setOpen((v) => !v)}>{open ? "Hide" : "Grade"}</button>
      </div>
      <p className="q-prompt" style={{ fontSize: 16, marginTop: 10 }}>{r.item?.prompt}</p>
      <div className="card" style={{ background: "var(--bg-2)", marginTop: 6 }}>
        <p className="small" style={{ whiteSpace: "pre-wrap", margin: 0 }}>{r.answer?.value || "(no answer)"}</p>
      </div>
      {r.item?.answer?.keywords?.length > 0 && (
        <p className="muted small" style={{ marginTop: 8 }}>Expected ideas: {r.item.answer.keywords.join(", ")}</p>
      )}
      {open && (
        <div style={{ marginTop: 12 }}>
          <label className="field-label">Awarded (out of {r.max_points})</label>
          <div className="row">
            <input type="range" min="0" max={r.max_points} step="0.5" value={awarded} onChange={(e) => setAwarded(Number(e.target.value))} style={{ flex: 1 }} />
            <span className="pill">{awarded}</span>
          </div>
          <label className="field-label">Feedback</label>
          <textarea className="ta" rows={2} value={feedback} onChange={(e) => setFeedback(e.target.value)} placeholder="Encouraging, specific feedback…" />
          <button className="btn primary" style={{ marginTop: 8 }} onClick={() => onGrade(r.attempt_id, r.id, awarded, feedback)}>Save grade</button>
        </div>
      )}
    </div>
  );
}
