// pages/TutorsPage.jsx — find a tutor from another country and hop into a call.
// Students browse teachers; teachers see open requests and accept them.

import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useStore } from "../store/app";

export default function TutorsPage() {
  const role = useStore((s) => s.user?.user?.role || "student");
  const [tutors, setTutors] = useState([]);
  const [mySessions, setMySessions] = useState([]);
  const [subject, setSubject] = useState("");
  const [topic, setTopic] = useState("");
  const [err, setErr] = useState("");

  const load = async () => {
    try {
      const q = subject ? `?course=${subject}` : "";
      const { data: t } = await api.get(`/api/v1/tutoring/tutors/${q}`);
      setTutors(Array.isArray(t) ? t : []);
    } catch { /* fine offline */ }
    try {
      const { data: s } = await api.get("/api/v1/tutoring/sessions/");
      const sessions = Array.isArray(s) ? s : s.results || [];
      setMySessions(sessions.filter((x) => x.status !== "ended" && x.status !== "cancelled"));
    } catch { /* fine */ }
  };

  useEffect(() => { load(); }, []);

  const requestSession = async (courseId, t) => {
    try {
      const { data } = await api.post("/api/v1/tutoring/sessions/", {
        course: courseId || null,
        topic: topic || "General",
      });
      setMySessions((s) => [...s, data]);
    } catch (e) {
      setErr(e.message);
    }
  };

  const accept = async (sid) => {
    try {
      await api.post(`/api/v1/tutoring/sessions/${sid}/accept/`);
      load();
    } catch (e) {
      setErr(e.message);
    }
  };

  const startCall = (sid) => (location.hash = `#/call/${sid}`);

  return (
    <div>
      <h1>📹 Tutoring</h1>
      <p className="muted">Face-to-face help from teachers anywhere — the call survives low bandwidth.</p>

      <section>
        <h2>Your sessions</h2>
        {mySessions.map((s) => (
          <div key={s.id} className="card row between">
            <div>
              <strong>#{s.id} · {s.course_name || "General"} · {s.topic}</strong>
              <div className="muted small">
                {s.status === "scheduled" && "Waiting for the other side…"}
                {s.status === "requested" && "No tutor yet — be patient"}
              </div>
            </div>
            {(s.status === "scheduled" || s.status === "active" || s.status === "requested") && (
              <div className="row">
                {role === "teacher" && s.status === "requested" && (
                  <button className="btn primary" onClick={() => accept(s.id)}>Accept</button>
                )}
                {(s.status === "scheduled" || s.status === "active") && (
                  <button className="btn primary" onClick={() => startCall(s.id)}>Join call →</button>
                )}
              </div>
            )}
          </div>
        ))}
        {mySessions.length === 0 && <p className="muted small">No open sessions.</p>}
      </section>

      {role === "student" && (
        <section>
          <h2>Find a tutor</h2>
          <div className="row">
            <select value={subject} onChange={(e) => setSubject(e.target.value)}>
              <option value="">Any subject</option>
              {["math", "english", "science", "computing"].map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <input placeholder="What do you need help with?" value={topic} onChange={(e) => setTopic(e.target.value)} />
          </div>
          <div className="grid tutors">
            {tutors.map((t) => (
              <div key={t.id} className="card tutor">
                <h3>{t.name}</h3>
                <div className="muted small">📍 {t.country || "?"} · ⭐ {t.rating}</div>
                <p className="small">{t.bio || "Experienced tutor"}</p>
                <button className="btn primary" onClick={() => requestSession(undefined, t)}>
                  Request a session
                </button>
              </div>
            ))}
          </div>
          {tutors.length === 0 && <p className="muted small">No tutors listed yet.</p>}
        </section>
      )}

      {err && <p className="error">{err}</p>}
      <Link className="btn sm" to="/dashboard">Back</Link>
    </div>
  );
}