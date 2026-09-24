// pages/LabsPage.jsx — coding, circuit, physics and science labs.

import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader";
import Empty from "../components/Empty";

const KIND_ICON = { coding: "💻", circuit: "🔌", physics: "🧲", science: "🔬" };
const KINDS = ["", "coding", "circuit", "physics", "science"];

export default function LabsPage() {
  const { t } = useI18n();
  const [rows, setRows] = useState([]);
  const [kind, setKind] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    (async () => {
      try {
        const { data } = await api.get("/api/v1/labs/labs/" + (kind ? `?kind=${kind}` : ""));
        setRows(Array.isArray(data) ? data : data.results || []);
      } catch {
        setErr("Couldn't load labs.");
      } finally {
        setLoading(false);
      }
    })();
  }, [kind]);

  return (
    <div>
      <PageHeader icon="🧪" title={t("labs")} subtitle="Hands-on labs that run on your device — no internet needed." />
      <div className="chips">
        {KINDS.map((k) => (
          <button key={k} className={"chip" + (kind === k ? " on" : "")} onClick={() => setKind(k)}>
            {k ? `${KIND_ICON[k]} ${k}` : "All"}
          </button>
        ))}
      </div>
      {err && <p className="error">{err}</p>}
      {!loading && rows.length === 0 && !err && <Empty icon="🧪" title="No labs yet" />}
      <div className="grid courses">
        {rows.map((l) => (
          <Link to={`/lab/${l.slug}`} key={l.slug} className="card course">
            <div className="course-thumb" style={{ background: "var(--accent-soft)", color: "#92600a" }}>
              <span>{KIND_ICON[l.kind] || "🧪"}</span>
            </div>
            <h3>{l.title}</h3>
            <p className="muted small">{l.prompt}</p>
            <div className="row between small muted" style={{ margin: "0 14px 14px" }}>
              <span className="badge kind">{l.kind}</span>
              <span>+{l.xp} XP</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
