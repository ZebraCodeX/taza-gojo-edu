// pages/LibraryPage.jsx — browse grade-6→college materials like a course store:
// subject tabs, search, grade/kind filters, and "save offline" on every card.
// The list + body are cached (SW + IndexedDB) so saved packs read with zero signal.

import React, { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { useStore } from "../store/app";
import { materialStore } from "../services/offline";

const SUBJECTS = [
  ["", "All subjects"],
  ["math", "Math"],
  ["english", "English"],
  ["science", "Science"],
  ["computing", "Computing"],
];
const KINDS = [
  ["", "Any kind"],
  ["study_pack", "Study packs (downloadable)"],
  ["book", "Books"],
  ["course", "Courses"],
  ["article", "Articles"],
  ["worksheet", "Worksheets"],
  ["video", "Videos"],
];
const GRADES = ["", 6, 7, 8, 9, 10, 11, 12, 13, 14, 99];
const gradeLabel = (g) => (g === 99 || g >= 13 ? "College" : `Grade ${g}`);

export default function LibraryPage() {
  const online = useStore((s) => s.online);
  const [params] = useSearchParams();
  const [materials, setMaterials] = useState([]);
  const [savedIds, setSavedIds] = useState(new Set());
  const [err, setErr] = useState("");
  const [subject, setSubject] = useState("");
  const [grade, setGrade] = useState("");
  const [kind, setKind] = useState("");
  const [q, setQ] = useState(params.get("q") || "");
  const [onlySaved, setOnlySaved] = useState(false);

  const load = async () => {
    (await materialStore.all()).forEach((m) =>
      setSavedIds((prev) => new Set(prev).add(m.id))
    );
    try {
      const { data } = await api.get("/api/v1/library/materials/");
      const list = Array.isArray(data) ? data : [];
      setMaterials(list);
      for (const m of list) await materialStore.save(m.id, m);
    } catch {
      setErr(online ? "Could not load the library right now." : "Offline — showing what's saved on this device.");
      const cached = await materialStore.all();
      setMaterials(cached);
    }
  };

  useEffect(() => { load(); }, []);

  const toggleSave = async (m) => {
    const { downloadMaterial } = await import("../services/offline");
    if (savedIds.has(m.id)) {
      await materialStore.remove(m.id);
      setSavedIds((prev) => { const s = new Set(prev); s.delete(m.id); return s; });
    } else {
      await downloadMaterial(m, { api });
      setSavedIds((prev) => new Set(prev).add(m.id));
    }
  };

  const filtered = useMemo(() => {
    let list = materials;
    if (subject) list = list.filter((m) => m.subject === subject);
    if (grade) {
      const g = Number(grade);
      list = list.filter((m) => m.grade_start <= g && m.grade_end >= g);
    }
    if (kind) list = list.filter((m) => m.kind === kind);
    if (q.trim()) {
      const t = q.trim().toLowerCase();
      list = list.filter(
        (m) => (m.title + " " + (m.description || "") + " " + (m.provider || "")).toLowerCase().includes(t)
      );
    }
    if (onlySaved) list = list.filter((m) => savedIds.has(m.id));
    return list;
  }, [materials, subject, grade, kind, q, onlySaved, savedIds]);

  const savedCount = savedIds.size;

  return (
    <div>
      <div className="row between">
        <div>
          <h1>📚 Library</h1>
          <p className="muted">
            Free books, courses, worksheets and AI study packs — grade 6 to college.
            <b> Save for offline</b> and keep learning with no signal.
          </p>
        </div>
        <span className={`pill ${online ? "" : "offline"}`}>
          {online ? "Online" : "Offline"} · {savedCount} saved
        </span>
      </div>
      {err && <p className="error">{err}</p>}

      <div className="filters card">
        <div className="chips row">
          {SUBJECTS.map(([v, label]) => (
            <button key={v || "all"} className={subject === v ? "chip on" : "chip"} onClick={() => setSubject(v)}>
              {label}
            </button>
          ))}
        </div>
        <div className="row">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search books, topics, providers…" />
          <select value={grade} onChange={(e) => setGrade(e.target.value)}>
            {GRADES.map((g) => (
              <option key={g} value={g}>{g === "" ? "Any level" : gradeLabel(Number(g))}</option>
            ))}
          </select>
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            {KINDS.map(([v, label]) => (
              <option key={v} value={v}>{label}</option>
            ))}
          </select>
          <label className="check">
            <input type="checkbox" checked={onlySaved} onChange={(e) => setOnlySaved(e.target.checked)} />
            Saved only
          </label>
        </div>
      </div>

      {filtered.length === 0 && <p className="muted center mt">Nothing here yet. Try another filter, or go online once to pull the catalog.</p>}

      <div className="grid mats">
        {filtered.map((m) => (
          <div key={m.id} className="card mat">
            <div className="mat-thumb" style={{ background: thumbColor(m.subject) }}>
              <span>{subjectIcon(m.subject)}</span>
              <span className="kind-flag">{m.kind.replace("_", " ")}</span>
            </div>
            <div className="mat-body">
              <h3>{m.title}</h3>
              <p className="muted small">{m.provider}{m.provider && m.license_note ? " · " : ""}{m.license_note}</p>
              <p className="small">{m.description}</p>
              <div className="row between meta">
                <span className="muted small">{m.grade_band}</span>
                <span className="muted small">
                  {savedIds.has(m.id) ? "✓ on this device" : `${m.downloads || 0} saved`}
                </span>
              </div>
              <div className="row actions">
                {m.downloadable ? (
                  <Link className="btn sm" to={`/library/read/${m.id}`}>Open</Link>
                ) : m.url ? (
                  <a className="btn sm" href={m.url} target="_blank" rel="noopener noreferrer">Source ↗</a>
                ) : null}
                <button
                  className={`btn sm ${savedIds.has(m.id) ? "" : "primary"}`}
                  onClick={() => toggleSave(m)}
                >
                  {savedIds.has(m.id) ? "Remove" : "Save offline"}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const COLORS = {
  math: "#4c6ef5", english: "#e8590c", science: "#099268", computing: "#7048a8", general: "#5f6b7a",
};
function thumbColor(subject) { return COLORS[subject] || COLORS.general; }
function subjectIcon(subject) {
  return { math: "🧮", english: "📖", science: "🔬", computing: "💻" }[subject] || "📚";
}