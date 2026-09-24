// pages/AssessmentRunnerPage.jsx — one-item-at-a-time assessment runner.
//
// The server serves the next item (adaptive or fixed), grades each answer and
// updates the ability estimate. This page renders whatever item kind arrives.

import React, { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import { useI18n } from "../i18n";
import { track } from "../services/events";

export default function AssessmentRunnerPage() {
  const { slug } = useParams();
  const { t } = useI18n();
  const [attemptId, setAttemptId] = useState(null);
  const [item, setItem] = useState(null);
  const [points, setPoints] = useState(1);
  const [index, setIndex] = useState(0);
  const [total, setTotal] = useState(0);
  const [answer, setAnswer] = useState({});
  const [feedback, setFeedback] = useState(null);
  const [summary, setSummary] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const startedAt = useRef(Date.now());

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.post(`/api/v1/assessment/assessments/${slug}/start/`, {});
        track("assessment_start", { object_type: "assessment", metadata: { slug } });
        setAttemptId(data.attempt_id);
        setItem(data.item);
        setPoints(data.points || 1);
        setIndex(data.index || 0);
        setTotal(data.total || 0);
      } catch {
        setErr("Could not start this assessment. Check your connection.");
      }
    })();
  }, [slug]);

  const reset = () => { setAnswer({}); setFeedback(null); };

  const submitAnswer = async () => {
    if (!item || busy) return;
    setBusy(true);
    try {
      const { data } = await api.post(`/api/v1/assessment/attempts/${attemptId}/answer/`, {
        item: item.id,
        answer,
        time_ms: Date.now() - startedAt.current,
      });
      startedAt.current = Date.now();
      setFeedback(data.result);
      setPoints(data.points || 1);
      setIndex(data.index || index + 1);
      setTotal(data.total || total);
      // Reveal feedback, then load the next item when the learner continues.
      window.__next = data.item;
    } catch {
      setErr("Could not submit that answer. It will be safe to retry.");
    } finally {
      setBusy(false);
    }
  };

  const nextItem = () => {
    const nxt = window.__next;
    window.__next = null;
    if (!nxt) return finish();
    setItem(nxt);
    reset();
  };

  const finish = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/api/v1/assessment/attempts/${attemptId}/submit/`);
      track("assessment_submit", { object_type: "assessment", value: data.percent, metadata: { slug } });
      setSummary(data);
    } catch {
      setErr("Could not finalise the attempt.");
    } finally {
      setBusy(false);
    }
  };

  if (err && !item) return <p className="error">{err}</p>;

  if (summary) {
    return (
      <div className="card result-card">
        <h1>{summary.passed ? "🎉 " + t("passed") : "💪 " + t("failed")}</h1>
        <p className="big-score">{summary.percent}%</p>
        <p className="muted">{summary.score} / {summary.max_score} points</p>
        {summary.certificate && (
          <div className="card cert-inline">
            <h3>🏅 {t("certificate")}: {summary.certificate.code}</h3>
            <Link className="btn primary" to="/certificates">View {t("certificates")}</Link>
          </div>
        )}
        <div className="row">
          <Link className="btn" to="/assessments">{t("assessments")}</Link>
          <Link className="btn ghost" to="/dashboard">{t("home")}</Link>
        </div>
      </div>
    );
  }

  if (!item) return <p>{t("loading")}</p>;

  return (
    <div className="runner">
      <div className="row between">
        <span className="pill">{t("question")} {Math.min(index + 1, total)} {t("of")} {total}</span>
        <button className="link" onClick={finish} disabled={busy}>{t("finish")}</button>
      </div>

      <div className="card q-card">
        <ItemPrompt item={item} answer={answer} setAnswer={setAnswer} disabled={!!feedback} />
      </div>

      {feedback ? (
        <div className={"card feedback " + (feedback.correct ? "ok" : "bad")}>
          <b>{feedback.correct ? "✓ " + t("correct") : "✗ " + t("tryAgain")}</b>
          {feedback.feedback && <p>{feedback.feedback}</p>}
          {feedback.explanation && <p className="muted small">{feedback.explanation}</p>}
          <button className="btn primary" onClick={nextItem}>{t("next")} →</button>
        </div>
      ) : (
        <button className="btn primary" onClick={submitAnswer} disabled={busy || !hasAnswer(item, answer)}>
          {busy ? "…" : t("submit")}
        </button>
      )}
      {err && <p className="error small">{err}</p>}
    </div>
  );
}

function hasAnswer(item, a) {
  switch (item.kind) {
    case "multi": return (a.values || []).length > 0;
    case "order": return (a.values || []).length > 0;
    case "match": return Object.keys(a.pairs || {}).length > 0;
    default: return (a.value ?? "") !== "";
  }
}

function ItemPrompt({ item, answer, setAnswer, disabled }) {
  const opts = item.options || [];

  if (item.kind === "mcq") {
    return (
      <>
        <h2 className="q-prompt">{item.prompt}</h2>
        <div className="opts">
          {opts.map((o) => {
            const id = o.id ?? o;
            const text = o.text ?? o;
            return (
              <button key={id} disabled={disabled} className={"opt" + (answer.value === id ? " on" : "")}
                onClick={() => setAnswer({ value: id })}>{text}</button>
            );
          })}
        </div>
        {item.hint && <p className="hint">💡 {item.hint}</p>}
      </>
    );
  }

  if (item.kind === "multi") {
    const values = answer.values || [];
    const toggle = (id) => {
      const set = new Set(values);
      set.has(id) ? set.delete(id) : set.add(id);
      setAnswer({ values: [...set] });
    };
    return (
      <>
        <h2 className="q-prompt">{item.prompt}</h2>
        <div className="opts">
          {opts.map((o) => {
            const id = o.id ?? o;
            const text = o.text ?? o;
            return (
              <button key={id} disabled={disabled} className={"opt" + (values.includes(id) ? " on" : "")}
                onClick={() => toggle(id)}>{text}</button>
            );
          })}
        </div>
        {item.hint && <p className="hint">💡 {item.hint}</p>}
      </>
    );
  }

  if (item.kind === "numeric") {
    return (
      <>
        <h2 className="q-prompt">{item.prompt}</h2>
        <div className="row">
          <input className="input" inputMode="decimal" placeholder="Answer" disabled={disabled}
            value={answer.value || ""} onChange={(e) => setAnswer({ ...answer, value: e.target.value })} />
          <input className="input unit" placeholder="unit" disabled={disabled}
            value={answer.unit || ""} onChange={(e) => setAnswer({ ...answer, unit: e.target.value })} />
        </div>
        {item.hint && <p className="hint">💡 {item.hint}</p>}
      </>
    );
  }

  if (item.kind === "order") {
    const values = answer.values || [];
    const remaining = opts.filter((o) => !values.includes(o));
    return (
      <>
        <h2 className="q-prompt">{item.prompt}</h2>
        <ol className="order-list">
          {values.map((v, i) => (
            <li key={v}>
              <span>{v}</span>
              {!disabled && (
                <span>
                  <button className="link" onClick={() => setAnswer({ values: values.filter((x) => x !== v) })}>✕</button>
                </span>
              )}
            </li>
          ))}
        </ol>
        {!disabled && remaining.length > 0 && (
          <div className="opts">
            {remaining.map((o) => (
              <button key={o} className="opt" onClick={() => setAnswer({ values: [...values, o] })}>+ {o}</button>
            ))}
          </div>
        )}
        {item.hint && <p className="hint">💡 {item.hint}</p>}
      </>
    );
  }

  if (item.kind === "match") {
    const pairs = answer.pairs || {};
    const left = item.options?.left || [];
    const right = item.options?.right || [];
    return (
      <>
        <h2 className="q-prompt">{item.prompt}</h2>
        <div className="match-grid">
          {left.map((l) => (
            <div className="match-row" key={l}>
              <span className="match-left">{l}</span>
              <select className="input" disabled={disabled} value={pairs[l] || ""}
                onChange={(e) => setAnswer({ pairs: { ...pairs, [l]: e.target.value } })}>
                <option value="">—</option>
                {right.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
          ))}
        </div>
        {item.hint && <p className="hint">💡 {item.hint}</p>}
      </>
    );
  }

  // short, code, math, essay
  return (
    <>
      <h2 className="q-prompt">{item.prompt}</h2>
      <textarea className="input" rows={item.kind === "essay" ? 6 : 2} disabled={disabled}
        value={answer.value || ""} onChange={(e) => setAnswer({ ...answer, value: e.target.value })}
        placeholder={item.kind === "code" ? "Type the program output" : "Your answer"} />
      {item.hint && <p className="hint">💡 {item.hint}</p>}
    </>
  );
}
