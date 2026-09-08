// pages/TutorsPage.jsx — Zoom-style tutoring scheduling.
//
// Students book a session for an exact slot (date + time + duration, like Zoom
// scheduling a meeting); teachers accept open requests. Three lists:
//   • Live / starting soon   — Join becomes available exactly when the window
//                              opens (5 min early, like Zoom's lobby).
//   • Upcoming               — booked slots, countdown to start, cancel.
//   • Past                   — finished calls, for recap.
// One refresh every 20s keeps everything fresh without heavy polling; a 1s
// timer drives the countdowns from the session's scheduled_at (client clock).

import React, { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { useStore } from "../store/app";

const DURATIONS = [15, 30, 45, 60];
const EARLY_MS = 5 * 60 * 1000;
const GRACE_MS = 15 * 60 * 1000;

function windowRange(s) {
  const start = new Date(s.scheduled_at).getTime();
  const end = start + (s.duration_minutes || 30) * 60 * 1000 + GRACE_MS;
  return { start, end };
}

function inWindow(s, now) {
  const { start } = windowRange(s);
  return now >= start - EARLY_MS;
}

function fmtCountdown(ms) {
  if (ms <= 0) return "now";
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
  return `${Math.floor(s / 86400)}d ${Math.floor((s % 86400) / 3600)}h`;
}

function fmtWhen(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

// Local datetime string for <input type="datetime-local">, defaulting to an
// hour from now so the scheduler is always "book it" ready.
function localWhen(offsetMs = 3600e3) {
  const d = new Date(Date.now() + offsetMs);
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

export default function TutorsPage() {
  const role = useStore((s) => s.user?.user?.role || "student");
  const student = role === "student";
  const [tutors, setTutors] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [showSchedule, setShowSchedule] = useState(false);
  const [subject, setSubject] = useState("");
  const [topic, setTopic] = useState("");
  const [when, setWhen] = useState(localWhen());
  const [duration, setDuration] = useState(30);
  const [err, setErr] = useState("");
  const [info, setInfo] = useState("");
  const [now, setNow] = useState(Date.now());
  const pollRef = useRef(null);

  const load = async () => {
    try {
      const q = subject ? `?course=${encodeURIComponent(subject)}` : "";
      const { data: t } = await api.get(`/api/v1/tutoring/tutors/${q}`);
      setTutors(Array.isArray(t) ? t : []);
    } catch { /* fine offline */ }
    try {
      const { data: s } = await api.get("/api/v1/tutoring/sessions/");
      setSessions(Array.isArray(s) ? s : s.results || []);
    } catch { /* fine */ }
  };

  useEffect(() => {
    load();
    pollRef.current = setInterval(load, 20000);
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => {
      clearInterval(pollRef.current);
      clearInterval(tick);
    };
  }, []);

  const schedule = async () => {
    setErr("");
    if (!when) { setErr("Pick a date & time (Zoom-style slot)."); return; }
    if (new Date(when) <= new Date()) { setErr("Pick a future time."); return; }
    const iso = new Date(when).toISOString(); // absolute time, timezone-safe
    try {
      const { data } = await api.post("/api/v1/tutoring/sessions/", {
        course: subject || null,
        topic: topic || "General",
        scheduled_at: iso,
        duration_minutes: duration,
      });
      setInfo(`Scheduled ✓ ${fmtWhen(data.scheduled_at)} · ${data.duration_minutes} min — your tutor can accept it from now on.`);
      setSessions((all) => [data, ...all]);
      setShowSchedule(false);
    } catch (e) {
      const d = e.response?.data;
      const msg = d ? d.scheduled_at || d.duration_minutes || d.detail || Object.values(d)[0] || "Could not schedule." : e.message;
      setErr(String(msg));
    }
  };

  const accept = async (sid) => {
    try { await api.post(`/api/v1/tutoring/sessions/${sid}/accept/`); load(); }
    catch (e) { setErr(e.message); }
  };

  const cancel = async (sid) => {
    try { await api.post(`/api/v1/tutoring/sessions/${sid}/cancel/`); load(); }
    catch (e) { setErr(e.message); }
  };

  const startCall = (sid) => (location.hash = `#/call/${sid}`);

  const live = sessions.filter((s) => (s.status === "scheduled" || s.status === "active") && inWindow(s, now));
  const upcoming = sessions.filter((s) => {
    if (s.status !== "scheduled" && s.status !== "active" && s.status !== "requested") return false;
    return !inWindow(s, now);
  });
  const past = sessions.filter((s) => s.status === "ended" || s.status === "cancelled");

  return (
    <div>
      <h1>📹 Tutoring</h1>
      <p className="muted">Book a slot, then join the video room exactly on time — it works even on slow connections.</p>

      {student && !showSchedule && (
        <button className="btn primary" onClick={() => { setShowSchedule(true); setWhen(localWhen()); }}>+ Schedule a session</button>
      )}

      {student && showSchedule && (
        <section className="card">
          <h2>Schedule a session</h2>
          <div className="row wrap">
            <select value={subject} onChange={(e) => setSubject(e.target.value)}>
              <option value="">Any subject</option>
              {["math", "english", "science", "computing"].map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <input placeholder="What do you need help with? (topic)" value={topic} onChange={(e) => setTopic(e.target.value)} />
            <label>
              Start
              <input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} />
            </label>
            <label>
              Duration
              <select value={duration} onChange={(e) => setDuration(Number(e.target.value))}>
                {DURATIONS.map((d) => <option key={d} value={d}>{d} min</option>)}
              </select>
            </label>
            <button className="btn primary" onClick={schedule}>Schedule</button>
            <button className="btn" onClick={() => setShowSchedule(false)}>Cancel</button>
          </div>
        </section>
      )}

      {info && <p className="success">{info}</p>}
      {err && <p className="error">{err}</p>}

      <section>
        <h2>▶ Live / starting now</h2>
        {live.map((s) => {
          const { start } = windowRange(s);
          const ready = now >= start - EARLY_MS;
          return (
            <div key={s.id} className="card row between">
              <div>
                <strong>{s.course_name || "General"} · {s.topic}</strong>
                <div className="muted small">
                  {(student ? s.tutor_name : s.student_name) ? `${student ? "Tutor" : "Student"}: ${student ? s.tutor_name : s.student_name} · ` : ""}
                  {fmtWhen(s.scheduled_at)}
                  {ready ? " · window open" : ` · starts in ${fmtCountdown(start - now)}`}
                </div>
              </div>
              <div className="row">
                {!student && s.status === "requested" && (
                  <button className="btn primary" onClick={() => accept(s.id)}>Accept</button>
                )}
                <button className="btn primary" disabled={!ready} onClick={() => startCall(s.id)}>
                  {ready ? "Join call →" : `Starts in ${fmtCountdown(start - now)}`}
                </button>
              </div>
            </div>
          );
        })}
        {live.length === 0 && <p className="muted small">Nothing live right now.</p>}
      </section>

      <section>
        <h2>📅 Upcoming &amp; open requests</h2>
        {upcoming.map((s) => {
          const { start } = windowRange(s);
          return (
            <div key={s.id} className="card row between">
              <div>
                <strong>#{s.id} · {s.course_name || "General"} · {s.topic}</strong>
                <div className="muted small">
                  {s.status === "requested" ? (
                    student
                      ? `Waiting for a tutor to accept${s.scheduled_at ? ` · starts in ${fmtCountdown(start - now)}` : ""}`
                      : s.student_name ? `Open request from ${s.student_name}` : "Open request"
                  ) : (
                    <>
                      {fmtWhen(s.scheduled_at)} · {s.duration_minutes} min
                      {s.status === "scheduled" ? ` · starts in ${fmtCountdown(start - now)}` : ""}
                    </>
                  )}
                </div>
              </div>
              <div className="row">
                {!student && s.status === "requested" && (
                  <button className="btn primary" onClick={() => accept(s.id)}>Accept</button>
                )}
                {student && s.status === "requested" && (
                  <button className="btn" onClick={() => cancel(s.id)}>Cancel request</button>
                )}
                {!student && s.status === "scheduled" && (
                  <button className="btn" onClick={() => cancel(s.id)}>Cancel</button>
                )}
              </div>
            </div>
          );
        })}
        {upcoming.length === 0 && <p className="muted small">No upcoming sessions.</p>}
      </section>

      {past.length > 0 && (
        <section>
          <h2>🗂 Past</h2>
          {past.map((s) => (
            <div key={s.id} className="card row between">
              <div>
                <strong>{s.course_name || "General"} · {s.topic}</strong>
                <div className="muted small">{fmtWhen(s.scheduled_at || s.started_at)} · {s.status} {s.rating ? `· ⭐ ${s.rating}` : ""}</div>
              </div>
            </div>
          ))}
        </section>
      )}

      {student && tutors.length > 0 && (
        <section>
          <h2>Tutors</h2>
          <div className="grid tutors">
            {tutors.map((t) => (
              <div key={t.id} className="card tutor">
                <h3>{t.name}</h3>
                <div className="muted small">📍 {t.country || "?"} · ⭐ {t.rating}</div>
                <p className="small">{t.bio || "Experienced tutor"}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      <button className="btn sm" onClick={() => (location.hash = "#/dashboard")}>Back</button>
    </div>
  );
}