// pages/ProgressPage.jsx — learner progress from learning analytics.

import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader";
import Empty from "../components/Empty";

export default function ProgressPage() {
  const { t } = useI18n();
  const [s, setS] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/api/v1/analytics/events/summary/");
        setS(data);
      } catch {
        setErr("Progress needs a connection to update.");
      }
    })();
  }, []);

  return (
    <div>
      <PageHeader icon="📈" title={t("progress")} subtitle="Your activity over the last 30 days." />
      {err && <p className="error">{err}</p>}
      {s && s.total_events === 0 && <Empty icon="📈" title="No activity yet" text="Complete a lesson or a lab and your progress will show up here." />}
      {s && s.total_events > 0 && (
        <>
          <div className="stat-cards">
            <div className="stat-card"><span className="sc-ico">📅</span><span><span className="sc-num">{s.active_days}</span><span className="sc-label">active days</span></span></div>
            <div className="stat-card"><span className="sc-ico">🎬</span><span><span className="sc-num">{Math.round(s.watch_seconds / 60)}</span><span className="sc-label">minutes of video</span></span></div>
            <div className="stat-card"><span className="sc-ico">⚡</span><span><span className="sc-num">{s.total_events}</span><span className="sc-label">activities</span></span></div>
            <div className="stat-card"><span className="sc-ico">📚</span><span><span className="sc-num">{(s.by_subject || []).length}</span><span className="sc-label">subjects touched</span></span></div>
          </div>
          <section className="card" style={{ marginTop: 18 }}>
            <h3>By subject</h3>
            {(s.by_subject || []).map((row) => {
              const max = Math.max(...s.by_subject.map((x) => x.n), 1);
              return (
                <div className="bar-row" key={row.subject}>
                  <span className="bar-label">{row.subject}</span>
                  <span className="bar" style={{ width: `${Math.max(6, (row.n / max) * 100)}%` }} />
                  <span className="muted small">{row.n}</span>
                </div>
              );
            })}
            {(!s.by_subject || s.by_subject.length === 0) && <p className="muted small">No subject activity yet.</p>}
          </section>
        </>
      )}
    </div>
  );
}
