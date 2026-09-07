// pages/ProfilePage.jsx — your school profile + learning roadmap.
// New students are walked through a short onboarding wizard (grade, interests,
// weekly minutes, goals). From anywhere you can edit your roadmap — those goals
// drive the dashboard and the curriculum planner.

import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { store, useStore } from "../store/app";

const SUBJECTS = ["math", "english", "science", "computing"];
const INTEREST_LABEL = { math: "🧮 Math", english: "📖 English", science: "🔬 Science", computing: "💻 Computing" };
const ROADMAP_IDEAS = [
  ["math", "Multiplication facts", "4"],
  ["math", "Fractions and decimals", "6"],
  ["english", "Reading with comprehension", "6"],
  ["english", "Writing good paragraphs", "8"],
  ["science", "The water cycle and weather", "4"],
  ["computing", "First steps in programming", "8"],
];

export default function ProfilePage() {
  const nav = useNavigate();
  const user = useStore((s) => s.user);
  const [profile, setProfile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/api/v1/auth/me/");
        setProfile(data);
        store.set({ user: data, points: data.points });
      } catch {
        setErr("Could not load your profile — try again when you're online.");
      }
    })();
  }, []);

  if (!profile) {
    return <div className="loading">⏳</div>;
  }

  const isStudent = profile.user?.role !== "teacher";
  const isOnboarding = isStudent && !profile.onboarded;

  const patch = async (body) => {
    setSaving(true);
    setMsg("");
    setErr("");
    try {
      const { data } = await api.patch("/api/v1/auth/me/", body);
      setProfile(data);
      store.set({ user: data, points: data.points });
      if (body.onboarded) setMsg("🎉 Your learning roadmap is ready!");
      else setMsg("Saved.");
    } catch (e) {
      setErr(e.message || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const toggleInterest = (s) => {
    const set = new Set(profile.interests || []);
    set.has(s) ? set.delete(s) : set.add(s);
    patch({ interests: [...set] });
  };

  const addGoal = (subject, goal, weeks) => {
    const goals = [...(profile.goals || []), { subject, goal, target_weeks: Number(weeks || 4) }];
    patch({ goals });
  };
  const removeGoal = (i) => {
    patch({ goals: (profile.goals || []).filter((_, ix) => ix !== i) });
  };

  if (isOnboarding) {
    return (
      <div className="profile-page">
        <section className="card wizard">
          <h1>🎒 Set up your learning plan</h1>
          <p className="muted">Three quick steps. Welcome to Taza-Gojo School!</p>

          <h2>1 · What grade are you in?</h2>
          <div className="grade-grid">
            {[6, 7, 8, 9, 10, 11, 12].map((g) => (
              <button
                key={g}
                className={profile.grade_level === g ? "grade-pill on" : "grade-pill"}
                onClick={() => patch({ grade_level: g })}
              >
                Grade {g}
              </button>
            ))}
          </div>
          {!profile.grade_level && <p className="muted small">Tap your grade to continue.</p>}

          <h2>2 · What do you want to learn? <span className="muted small">(pick any)</span></h2>
          <div className="chiprow">
            {SUBJECTS.map((s) => (
              <button
                key={s}
                className={(profile.interests || []).includes(s) ? "chip on" : "chip"}
                onClick={() => toggleInterest(s)}
              >
                {INTEREST_LABEL[s] || s}
              </button>
            ))}
          </div>

          <h2>3 · Your goals <span className="muted small">(at least one)</span></h2>
          <p className="muted small">We'll show these on your dashboard and plan around them.</p>
          <div className="goal-suggest">
            {ROADMAP_IDEAS.map(([subject, goal, weeks]) => (
              <button key={goal} className="suggest-chip" onClick={() => addGoal(subject, goal, weeks)}
                disabled={(profile.goals || []).some((g) => g.goal === goal)}>
                {SUBJECT_ICONS[subject]} {goal} · ~{weeks}wk
              </button>
            ))}
          </div>
          {profile.goals?.length > 0 && (
            <div className="goals-list">
              {profile.goals.map((g, i) => (
                <div className="goal-chip owned" key={i}>
                  {SUBJECT_ICONS[g.subject]} <b>{g.goal}</b>
                  <small>{g.target_weeks} wk</small>
                  <button className="linkbtn" onClick={() => removeGoal(i)}>✕</button>
                </div>
              ))}
            </div>
          )}

          <h2>Time you can give each week</h2>
          <div className="row">
            <input
              type="range" min={30} max={600} step={30}
              value={profile.weekly_minutes || 120}
              onChange={(e) => setProfile({ ...profile, weekly_minutes: Number(e.target.value) })}
            />
            <span className="pill">{profile.weekly_minutes || 120} min/wk</span>
          </div>

          <button
            className="btn primary block"
            disabled={saving || !profile.grade_level || !(profile.goals?.length)}
            onClick={() => patch({ weekly_minutes: profile.weekly_minutes, onboarded: true })}
          >
            {saving ? "Saving…" : "Start learning 🚀"}
          </button>
          {err && <p className="error">{err}</p>}
          {msg && <p className="success">{msg}</p>}
        </section>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <div className="row between">
        <h1>👤 My profile</h1>
        <span className="pill">{isStudent ? "Student" : "Teacher"}</span>
      </div>

      <section className="card profile-hero">
        <div className="row">
          <span className="avatar big">{isStudent ? "🧑🏽‍🎓" : "👩🏽‍🏫"}</span>
          <div>
            <h2>{profile.user?.username}</h2>
            <p className="muted small">
              {profile.user?.country || "—"}
              {profile.grade_level ? ` · Grade ${profile.grade_level}` : ""}
              {" · member since " + (profile.created_at ? profile.created_at.slice(0, 10) : "—")}
            </p>
          </div>
        </div>
        <div className="stat-row">
          <div className="stat"><b>{profile.points}</b><span>points</span></div>
          <div className="stat"><b>{profile.streak_days}</b><span>day streak</span></div>
          <div className="stat"><b>{profile.weekly_minutes || 0}</b><span>min / week</span></div>
        </div>
      </section>

      {isStudent && (
        <section className="card">
          <h2>🗺 Learning roadmap</h2>
          {profile.goals?.length > 0 ? (
            <div className="goals-list">
              {profile.goals.map((g, i) => (
                <div className="goal-chip owned" key={i}>
                  {SUBJECT_ICONS[g.subject]} <b>{g.goal}</b>
                  <small>{g.target_weeks} wk</small>
                  <button className="linkbtn" onClick={() => removeGoal(i)}>✕</button>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted small">No goals yet — add a few and we'll plan your next steps.</p>
          )}
          {ROADMAP_IDEAS.filter(([, goal]) => !(profile.goals || []).some((g) => g.goal === goal)).map(([subject, goal, weeks]) => (
            <button key={goal} className="suggest-chip" onClick={() => addGoal(subject, goal, weeks)}>
              {SUBJECT_ICONS[subject]} Add: {goal}
            </button>
          ))}
          <h2>Interests</h2>
          <div className="chiprow">
            {SUBJECTS.map((s) => (
              <button key={s} className={(profile.interests || []).includes(s) ? "chip on" : "chip"}
                onClick={() => { toggleInterest(s); }}>
                {INTEREST_LABEL[s] || s}
              </button>
            ))}
          </div>
        </section>
      )}

      {!isStudent && (
        <section className="card">
          <h2>Teaching profile</h2>
          <label className="field-label">Subjects I teach</label>
          <div className="chiprow">
            {SUBJECTS.map((s) => {
              const on = (profile.subjects || []).includes(s);
              return (
                <button key={s} className={on ? "chip on" : "chip"} onClick={() => {
                  const set = new Set(profile.subjects || []);
                  on ? set.delete(s) : set.add(s);
                  patch({ subjects: [...set] });
                }}>
                  {INTEREST_LABEL[s] || s}
                </button>
              );
            })}
          </div>
          <label className="field-label">Bio</label>
          <textarea className="ta" rows={3} defaultValue={profile.bio} onBlur={(e) => patch({ bio: e.target.value })} />
          <label className="field-label">Timezone</label>
          <input defaultValue={profile.timezone} onBlur={(e) => patch({ timezone: e.target.value })} placeholder="e.g. Africa/Nairobi" />
        </section>
      )}

      <section className="card">
        <h2>Preferences</h2>
        <label className="field-label">Your connection speed (chooses video quality)</label>
        <select value={profile.device_bandwidth} onChange={(e) => patch({ device_bandwidth: e.target.value })}>
          <option value="low">Low — 2G</option>
          <option value="medium">Medium — 3G</option>
          <option value="high">High — 4G</option>
        </select>
        <label className="field-label">Weekly study time</label>
        <div className="row">
          <input
            type="range" min={30} max={600} step={30}
            value={profile.weekly_minutes || 120}
            onChange={(e) => setProfile({ ...profile, weekly_minutes: Number(e.target.value) })}
          />
          <span className="pill" style={{ minWidth: 120 }}>{profile.weekly_minutes || 120} min/wk</span>
          <button className="btn sm primary" disabled={saving} onClick={() => patch({ weekly_minutes: profile.weekly_minutes })}>
            Save
          </button>
        </div>
        {msg && <p className="success">{msg}</p>}
        {err && <p className="error">{err}</p>}
      </section>

      <button className="linkbtn" onClick={() => nav("/dashboard")}>← Back to learning</button>
    </div>
  );
}

const SUBJECT_ICONS = { math: "🧮", english: "📖", science: "🔬", computing: "💻", general: "🎯" };