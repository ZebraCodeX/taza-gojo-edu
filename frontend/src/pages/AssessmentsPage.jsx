// pages/AssessmentsPage.jsx — the assessment hub: quizzes, practice and exams.

import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader";
import Empty from "../components/Empty";

const SUBJECT_ICON = { physics: "🧲", electricity: "⚡", math: "🧮", science: "🔬", computing: "💻", english: "📖" };
const SUBJECTS = ["", "physics", "electricity", "math", "computing", "english", "science"];

export default function AssessmentsPage() {
  const { t } = useI18n();
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");
  const [subject, setSubject] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    (async () => {
      try {
        const { data } = await api.get("/api/v1/assessment/assessments/" + (subject ? `?subject=${subject}` : ""));
        setRows(Array.isArray(data) ? data : data.results || []);
      } catch {
        setErr("Couldn't load assessments. You can still open one you started earlier.");
      } finally {
        setLoading(false);
      }
    })();
  }, [subject]);

  return (
    <div>
      <PageHeader
        icon="📝"
        title={t("assessments")}
        subtitle="Auto-graded tests with instant feedback. Adaptive sets adjust to your level."
        actions={<Link className="btn sm" to="/certificates">🏅 {t("certificates")}</Link>}
      />

      <div className="chips">
        {SUBJECTS.map((s) => (
          <button key={s} className={"chip" + (subject === s ? " on" : "")} onClick={() => setSubject(s)}>
            {s ? `${SUBJECT_ICON[s] || "•"} ${t(s)}` : "All"}
          </button>
        ))}
      </div>

      {err && <p className="error">{err}</p>}
      {!loading && rows.length === 0 && !err && (
        <Empty icon="📝" title="No assessments yet" text="Once your teacher publishes a test it will appear here." />
      )}
      <div className="grid courses">
        {rows.map((a) => (
          <Link to={`/assessment/${a.slug}`} key={a.slug} className="card course">
            <div className="course-thumb" style={{ background: "var(--sky-soft)", color: "var(--sky)" }}>
              <span>{SUBJECT_ICON[a.subject] || "📝"}</span>
            </div>
            <h3>{a.title}</h3>
            <p className="muted small">{a.description}</p>
            <div className="row between small muted" style={{ margin: "0 14px 14px" }}>
              <span className="badge kind">{a.kind}</span>
              <span>{a.adaptive ? "adaptive · " : ""}{a.max_items} items · pass {a.pass_score}%</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
