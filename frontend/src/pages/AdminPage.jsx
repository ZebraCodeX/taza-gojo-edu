// pages/AdminPage.jsx — the in-app school admin panel for teachers/admins.
// Overview stats, material management (create/activate/edit/delete) and
// student/teacher accounts. Guarded server-side by the adminapi permission.

import React, { useEffect, useState } from "react";
import { api } from "../api/client";

const TABS = [
  ["overview", "📊 Overview"],
  ["materials", "📚 Materials"],
  ["users", "👥 Users"],
];

export default function AdminPage() {
  const [tab, setTab] = useState("overview");
  const [stats, setStats] = useState(null);
  const [materials, setMaterials] = useState([]);
  const [users, setUsers] = useState([]);
  const [q, setQ] = useState("");
  const [mQ, setMQ] = useState("");
  const [err, setErr] = useState("");

  const loadStats = async () => {
    try { const { data } = await api.get("/api/v1/admin/stats/"); setStats(data); }
    catch (e) { setErr(e.message || "Admin access required."); }
  };
  const loadMaterials = async () => {
    try {
      const { data } = await api.get(`/api/v1/admin/materials/?q=${encodeURIComponent(mQ)}&size=100`);
      setMaterials(data.results || []);
    } catch (e) { setErr(e.message); }
  };
  const loadUsers = async () => {
    try {
      const { data } = await api.get(`/api/v1/admin/users/?q=${encodeURIComponent(q)}`);
      setUsers(Array.isArray(data) ? data : []);
    } catch (e) { setErr(e.message); }
  };

  useEffect(() => {
    loadStats();
    loadMaterials();
    loadUsers();
  }, []);

  if (err) return <p className="error center mt">{err}</p>;

  return (
    <div className="admin">
      <div className="row between">
        <h1>🛠 School admin</h1>
        <span className="muted small">teachers & admins</span>
      </div>

      <div className="tabs">
        {TABS.map(([v, label]) => (
          <button key={v} className={`tab ${tab === v ? "on" : ""}`} onClick={() => setTab(v)}>{label}</button>
        ))}
      </div>

      {tab === "overview" && stats && (
        <div className="stat-grid">
          {[
            ["👥 Students", stats.students],
            ["👩🏽‍🏫 Teachers", stats.teachers],
            ["🧑🏽‍💼 Admins", stats.admins],
            ["🎓 Users total", stats.users],
            ["📚 Materials", stats.materials],
            ["✅ Live materials", stats.materials_live],
            ["⬇️ Downloads", stats.downloads],
            ["📗 Lessons done", stats.lessons_done],
            ["🗂 Courses", stats.courses],
          ].map(([label, val]) => (
            <div className="card stat" key={label}>
              <b>{val}</b>
              <span>{label}</span>
            </div>
          ))}
        </div>
      )}

      {tab === "materials" && (
        <section>
          <div className="row">
            <input value={mQ} onChange={(e) => setMQ(e.target.value)} placeholder="Search materials…"
              onKeyDown={(e) => e.key === "Enter" && loadMaterials()} />
            <button className="btn" onClick={loadMaterials}>Search</button>
          </div>
          <div className="admin-table card">
            {materials.map((m) => (
              <div className="admin-row" key={m.id}>
                <div className="admin-row-main">
                  <strong>{m.title}</strong>
                  <span className="muted small">{m.subject} · {m.kind} · {m.provider} · {m.downloads} saves</span>
                </div>
                <div className="row">
                  <span className={`pill ${m.active ? "" : "offline"}`}>{m.active ? "Live" : "Hidden"}</span>
                  <button className="btn sm" onClick={async () => {
                    await api.patch(`/api/v1/admin/materials/${m.id}/`, { active: !m.active });
                    loadMaterials();
                  }}>
                    {m.active ? "Deactivate" : "Activate"}
                  </button>
                  <button className="btn sm danger" onClick={async () => {
                    if (confirm(`Really delete "${m.title}"? Saved copies stay on old devices.`)) {
                      await api.del(`/api/v1/admin/materials/${m.id}/`);
                      loadMaterials();
                    }
                  }}>Delete</button>
                </div>
              </div>
            ))}
            {materials.length === 0 && <p className="muted small">No materials match.</p>}
          </div>
        </section>
      )}

      {tab === "users" && (
        <section>
          <div className="row">
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search students & teachers…"
              onKeyDown={(e) => e.key === "Enter" && loadUsers()} />
            <button className="btn" onClick={loadUsers}>Search</button>
          </div>
          <div className="admin-table card">
            {users.map((u) => (
              <div className="admin-row" key={u.id}>
                <div className="admin-row-main">
                  <strong>{u.username}</strong>
                  <span className="muted small">
                    {u.role} · {u.country || "—"} · {u.points} pts · {u.lessons_done} lessons · joined {u.joined?.slice(0, 10)}
                  </span>
                </div>
                <div className="row">
                  <span className={`pill ${u.is_active ? "" : "offline"}`}>{u.is_active ? "Active" : "Disabled"}</span>
                  <button className="btn sm" onClick={async () => {
                    await api.patch(`/api/v1/admin/users/${u.id}/`, { is_active: !u.is_active });
                    loadUsers();
                  }}>
                    {u.is_active ? "Disable" : "Enable"}
                  </button>
                </div>
              </div>
            ))}
            {users.length === 0 && <p className="muted small">No users match.</p>}
          </div>
        </section>
      )}
    </div>
  );
}