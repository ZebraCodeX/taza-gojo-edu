// pages/LabRunnerPage.jsx — run a lab: code in the browser or drive a sim,
// then check the tests and submit the result (works offline; syncs later).

import React, { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import { useI18n } from "../i18n";
import CodeLab from "../components/CodeLab";
import { Sim } from "../components/sims";
import { track } from "../services/events";

function approx(a, b) {
  const na = Number(a), nb = Number(b);
  if (Number.isFinite(na) && Number.isFinite(nb)) return Math.abs(na - nb) <= Math.max(0.1, Math.abs(nb) * 0.05);
  return a === b;
}

export default function LabRunnerPage() {
  const { slug } = useParams();
  const { t } = useI18n();
  const [lab, setLab] = useState(null);
  const [simState, setSimState] = useState({});
  const [codeResults, setCodeResults] = useState([]);
  const [submission, setSubmission] = useState(null);
  const [err, setErr] = useState("");
  const codeRef = useRef({ code: "", output: "" });

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get(`/api/v1/labs/labs/${slug}/`);
        setLab(data);
      } catch {
        setErr("This lab isn't available offline yet.");
      }
    })();
  }, [slug]);

  if (err && !lab) return <p className="error">{err}</p>;
  if (!lab) return <p>{t("loading")}</p>;

  const isCode = lab.kind === "coding";

  const evaluate = () => {
    return (lab.tests || []).map((tc) => {
      if ("expected_output" in tc) {
        const r = codeResults.find((x) => x.name === tc.name);
        return { name: tc.name, passed: !!r?.passed };
      }
      const got = simState[tc.expr];
      return { name: tc.name, passed: approx(got, tc.expected) };
    });
  };

  const submit = async () => {
    const results = evaluate();
    try {
      const { data } = await api.post(`/api/v1/labs/labs/${lab.slug}/submit/`, {
        code: codeRef.current.code,
        language: lab.language,
        results,
      });
      track("lab_submit", { subject: lab.subject, object_type: "lab", value: data.score });
      setSubmission(data);
    } catch {
      setErr("Couldn't submit right now — your work is safe, try again when online.");
    }
  };

  return (
    <div>
      <Link className="linkbtn" to="/labs">← {t("labs")}</Link>
      <h1>{lab.title}</h1>
      <p className="muted">{lab.prompt}</p>
      {lab.instructions && <p className="small">{lab.instructions}</p>}

      {isCode ? (
        <CodeLab lab={lab} onChange={(r) => { setCodeResults(r.results || []); codeRef.current = { code: r.code, output: r.output }; }} />
      ) : (
        <Sim assets={lab.assets} onChange={setSimState} />
      )}

      <div className="row" style={{ marginTop: 12 }}>
        <button className="btn primary" onClick={submit}>{t("check")} & {t("submit")}</button>
      </div>

      {submission && (
        <div className={"card " + (submission.passed ? "success" : "")}>
          <b>{submission.passed ? "✓ " + t("passed") : t("failed")}</b>
          <span className="muted small"> · {submission.passed_tests}/{submission.total_tests} {t("testsPassed")}</span>
        </div>
      )}
      {err && <p className="error small">{err}</p>}
    </div>
  );
}
