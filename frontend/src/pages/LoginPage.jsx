// pages/LoginPage.jsx — register (student/teacher) or sign in.

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, register } from "../api/client";
import { store } from "../store/app";

export default function LoginPage() {
  const nav = useNavigate();
  const [tab, setTab] = useState("login");
  const [form, setForm] = useState({ username: "", password: "", role: "student", country: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (tab === "login") {
        await login(form.username, form.password);
      } else {
        await register(form);
        await login(form.username, form.password);
      }
      const { data } = await import("../api/client").then((m) => m.api.get("/api/v1/auth/me/"));
      store.set({ user: data });
      store.set({ points: data.points });
      nav(data.user?.role === "teacher" ? "/tutors" : "/dashboard");
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth">
      <div className="card auth-card">
        <h1>🎓 Taza-Gojo EDU</h1>
        <p className="muted">Game-based learning + live tutoring, built for low-bandwidth networks.</p>
        <div className="tabs">
          <button className={tab === "login" ? "tab on" : "tab"} onClick={() => setTab("login")}>Sign in</button>
          <button className={tab === "register" ? "tab on" : "tab"} onClick={() => setTab("register")}>Create account</button>
        </div>
        <form onSubmit={submit}>
          <input placeholder="Username" value={form.username} required autoComplete="username"
            onChange={(e) => setForm({ ...form, username: e.target.value })} />
          <input type="password" placeholder="Password (min 6 chars)" value={form.password} required minLength={6}
            autoComplete={tab === "login" ? "current-password" : "new-password"}
            onChange={(e) => setForm({ ...form, password: e.target.value })} />
          {tab === "register" && (
            <>
              <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="student">I am a student</option>
                <option value="teacher">I am a teacher / tutor</option>
              </select>
              <input placeholder="Country (e.g. Kenya, Ghana, Nigeria)" value={form.country}
                onChange={(e) => setForm({ ...form, country: e.target.value })} />
            </>
          )}
          <button className="btn primary block" disabled={busy}>{busy ? "Working…" : tab === "login" ? "Sign in" : "Create my account"}</button>
        </form>
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  );
}