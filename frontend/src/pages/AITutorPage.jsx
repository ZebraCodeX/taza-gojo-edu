// pages/AITutorPage.jsx — chat with the AI tutor agent. One round-trip per
// message (see TutorAskView) so a spotty connection still gets one answer.
// The tutor answers with steps, suggests follow-up chips, and says which study
// notes it based its answer on.

import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import { useStore } from "../store/app";

const SUBJECTS = [
  ["math", "🧮 Math"],
  ["english", "📖 English"],
  ["science", "🔬 Science"],
  ["computing", "💻 Computing"],
];

export default function AITutorPage() {
  const profile = useStore((s) => s.user);
  const [msgs, setMsgs] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [subject, setSubject] = useState("math");
  const [followUps, setFollowUps] = useState([]);

  const ask = async (raw) => {
    const question = String(raw || "").trim();
    if (!question || busy) return;
    setText("");
    setFollowUps([]);
    setMsgs((m) => [...m, { role: "user", text: question }]);
    setBusy(true);
    try {
      const { data } = await api.post("/api/v1/agents/tutor/ask/", { message: question, subject });
      setMsgs((m) => [...m, { role: "agent", text: data.text }]);
      setFollowUps(data.follow_ups || []);
      if (data.context?.length) {
        setMsgs((m) => [...m.slice(0, -1), { ...m[m.length - 1], notes: data.context }]);
      }
    } catch {
      setMsgs((m) => [...m, { role: "agent", text: "I couldn't reach my model. Try again in a moment." }]);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    const box = document.getElementById("chat");
    if (box) box.scrollTop = box.scrollHeight;
  }, [msgs, busy, followUps]);

  return (
    <div className="chat-page">
      <div className="row between">
        <h1>💬 AI Tutor</h1>
        {(profile?.grade_level || profile?.interests?.length) && (
          <span className="muted small">
            {profile?.grade_level ? `Grade ${profile.grade_level} · ` : ""}
            {(profile?.interests || []).join(" + ")}
          </span>
        )}
      </div>
      <p className="muted small">
        Ask anything from your lessons. The tutor answers in steps, from materials
        in the library — and won't just hand you the answer for homework.
      </p>
      <div className="subject-row">
        {SUBJECTS.map(([s, label]) => (
          <button key={s} className={subject === s ? "btn primary sm" : "btn sm"} onClick={() => setSubject(s)}>
            {label}
          </button>
        ))}
      </div>
      <div id="chat" className="chat">
        <div className="msg agent">
          Hi! I'm your {subject} tutor. Ask me to explain anything, solve a problem, or
          give you a practice question. Say things like <i>"12 × 9"</i> or <i>"how do I
          find 25% of 80?"</i>
        </div>
        {msgs.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.text}
            {m.notes?.length > 0 && (
              <div className="notes">📘 based on your notes: {m.notes.join(", ")}</div>
            )}
          </div>
        ))}
        {busy && <div className="msg agent dim">thinking…</div>}
      </div>
      {followUps.length > 0 && (
        <div className="followups">
          {followUps.map((f, i) => (
            <button key={i} className="chip" onClick={() => ask(f)}>{f}</button>
          ))}
        </div>
      )}
      <form className="chat-form" onSubmit={(e) => { e.preventDefault(); ask(text); }}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask a question…" disabled={busy} />
        <button className="btn primary" disabled={busy}>Send</button>
      </form>
    </div>
  );
}