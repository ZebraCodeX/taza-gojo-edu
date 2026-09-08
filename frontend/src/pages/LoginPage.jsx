// pages/LoginPage.jsx - the school gates. A calm two-panel layout: brand story
// on the left (folded to a slim header on phones), the sign-in / create-account
// card on the right. Fixed form height means switching tabs never makes the
// page jump, and each action is one fast round trip on slow links.

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, register, api } from "../api/client";
import { store } from "../store/app";

const FEATURES = [
  ["\u{1F3AE}", "Game-based lessons that play with zero signal"],
  ["\u{1F4DA}", "A free library you can download for offline study"],
  ["\u{1F4F9}", "Face-to-face video help from real teachers"],
  ["\u{1F4D6}", "Video lectures and study packs for every topic"],
];

const DEMO_ACCOUNTS = [
  ["ada", "test1234", "Student", "Kenya"],
  ["mrkwame", "test1234", "Teacher", "Ghana"],
];

export default function LoginPage() {
  const nav = useNavigate();
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [regForm, setRegForm] = useState({ username: "", password: "", role: "student", country: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showPw, setShowPw] = useState(false);

  const enter = (profile) => {
    store.set({ user: profile, points: profile.points });
    nav("/dashboard");
  };

  const finishLogin = async () => {
    const { data } = await api.get("/api/v1/auth/me/");
    enter(data);
  };

  const submit = async (e) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      if (mode === "login") {
        await login(loginForm.username.trim(), loginForm.password);
        await finishLogin();
      } else {
        // register() stores the returned tokens, so signup signs you straight in.
        const data = await register({ ...regForm });
        enter(data.user);
      }
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const demoTap = async (username, password) => {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await login(username, password);
      await finishLogin();
    } catch (err) {
      setError(err.message || "Could not use the demo account.");
    } finally {
      setBusy(false);
    }
  };

  const switchMode = (m) => {
    setMode(m);
    setError("");
    setShowPw(false);
  };

  return (
    <div className="auth">
      <aside className="auth-brand">
        <div className="brand-big">
          <span className="brand-mark lg">Tz</span>
          <span>
            <b>Taza-Gojo</b>
            <small>School</small>
          </span>
        </div>
        <h1>Learn anything. Anywhere. Even with no signal.</h1>
        <p className="auth-tagline">
          An online secondary school for students on low-bandwidth networks —
          courses, video lectures, free books and live face-to-face teachers,
          all in one place.
        </p>
        <ul className="feature-list">
          {FEATURES.map(([ico, txt]) => (
            <li key={txt}>
              <span className="feature-ico">{ico}</span>
              <span>{txt}</span>
            </li>
          ))}
        </ul>
        <div className="auth-proof">
          <span className="pill">Works offline</span>
          <span className="pill">Free &amp; open materials</span>
          <span className="pill">Made for 2G</span>
        </div>
      </aside>

      <section className="auth-panel">
        <div className="auth-card">
          <div className="auth-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "login"}
              className={mode === "login" ? "auth-tab on" : "auth-tab"}
              onClick={() => switchMode("login")}
            >
              Sign in
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "register"}
              className={mode === "register" ? "auth-tab on" : "auth-tab"}
              onClick={() => switchMode("register")}
            >
              Create account
            </button>
          </div>

          <form className="auth-form" onSubmit={submit} noValidate>
            {mode === "login" ? (
              <>
                <label className="auth-field">
                  <span>Username</span>
                  <input
                    value={loginForm.username}
                    onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })}
                    placeholder="e.g. ada"
                    autoComplete="username"
                    autoFocus
                    required
                  />
                </label>
                <label className="auth-field">
                  <span>Password</span>
                  <div className="pwd-wrap">
                    <input
                      type={showPw ? "text" : "password"}
                      value={loginForm.password}
                      onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                      placeholder="Your password"
                      autoComplete="current-password"
                      required
                    />
                    <button type="button" className="pwd-toggle" onClick={() => setShowPw(!showPw)} aria-label="Show password">
                      {showPw ? "Hide" : "Show"}
                    </button>
                  </div>
                </label>
              </>
            ) : (
              <>
                <label className="auth-field">
                  <span>Username</span>
                  <input
                    value={regForm.username}
                    onChange={(e) => setRegForm({ ...regForm, username: e.target.value })}
                    placeholder="Pick a username"
                    autoComplete="username"
                    autoFocus
                    required
                  />
                </label>
                <label className="auth-field">
                  <span>Password</span>
                  <div className="pwd-wrap">
                    <input
                      type={showPw ? "text" : "password"}
                      value={regForm.password}
                      onChange={(e) => setRegForm({ ...regForm, password: e.target.value })}
                      placeholder="At least 6 characters"
                      minLength={6}
                      autoComplete="new-password"
                      required
                    />
                    <button type="button" className="pwd-toggle" onClick={() => setShowPw(!showPw)} aria-label="Show password">
                      {showPw ? "Hide" : "Show"}
                    </button>
                  </div>
                </label>
                <div className="auth-field">
                  <span>I am a…</span>
                  <div className="role-picker">
                    {[
                      ["student", "Student"],
                      ["teacher", "Teacher / tutor"],
                    ].map(([v, label]) => (
                      <button
                        type="button"
                        key={v}
                        className={regForm.role === v ? "role-btn on" : "role-btn"}
                        onClick={() => setRegForm({ ...regForm, role: v })}
                      >
                        {v === "student" ? "\u{1F9D2}" : "\u{1F469}"} {label}
                      </button>
                    ))}
                  </div>
                </div>
                <label className="auth-field">
                  <span>Country (optional)</span>
                  <input
                    value={regForm.country}
                    onChange={(e) => setRegForm({ ...regForm, country: e.target.value })}
                    placeholder="e.g. Kenya, Ghana, Nigeria"
                    autoComplete="country-name"
                  />
                </label>
              </>
            )}

            {error && <div className="alert" role="alert">{error}</div>}

            <button className="btn submit" disabled={busy}>
              {busy ? (
                <><span className="spinner" aria-hidden /> One moment…</>
              ) : mode === "login" ? (
                "Sign in"
              ) : (
                "Create my account"
              )}
            </button>
          </form>

          <div className="demo-box">
            <span className="demo-label">Prefer a quick tour?</span>
            <div className="demo-row">
              {DEMO_ACCOUNTS.map(([username, password, role, country]) => (
                <button type="button" key={username} className="demo-btn" disabled={busy} onClick={() => demoTap(username, password)}>
                  <span className="demo-avatar">{role === "Teacher" ? "\u{1F469}" : "\u{1F9D2}"}</span>
                  <span className="demo-txt">
                    <b>{role}</b>
                    <small>{country}</small>
                  </span>
                </button>
              ))}
            </div>
          </div>

          <p className="auth-foot">
            {mode === "login" ? "New here? " : "Already have an account? "}
            <button type="button" className="linkbtn" onClick={() => switchMode(mode === "login" ? "register" : "login")}>
              {mode === "login" ? "Create your account" : "Sign in instead"}
            </button>
          </p>
        </div>
      </section>
    </div>
  );
}