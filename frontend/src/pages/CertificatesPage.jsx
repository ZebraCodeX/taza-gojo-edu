// pages/CertificatesPage.jsx — earned certificates, printable and verifiable.

import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader";
import Empty from "../components/Empty";

export default function CertificatesPage() {
  const { t } = useI18n();
  const [rows, setRows] = useState([]);
  const [verifyCode, setVerifyCode] = useState("");
  const [verifyResult, setVerifyResult] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/api/v1/assessment/certificates/");
        setRows(Array.isArray(data) ? data : data.results || []);
      } catch {
        setErr("Couldn't load certificates.");
      }
    })();
  }, []);

  const verify = async () => {
    setVerifyResult(null);
    try {
      const { data } = await api.get(`/api/v1/assessment/certificates/verify/${verifyCode.trim()}/`);
      setVerifyResult(data);
    } catch {
      setVerifyResult({ valid: false });
    }
  };

  return (
    <div>
      <PageHeader icon="🏅" title={t("certificates")} subtitle="Every certificate has a unique code anyone can verify." />

      {err && <p className="error">{err}</p>}
      {rows.length === 0 && !err && (
        <Empty icon="🏅" title="No certificates yet" text="Pass an assessment to earn your first certificate." action={<a className="btn primary" href="#/assessments">Go to assessments</a>} />
      )}
      <div className="grid courses">
        {rows.map((c) => (
          <div className="card cert" key={c.id}>
            <div className="cert-seal">🏅</div>
            <h3>{c.title}</h3>
            <p className="muted small">{c.subject} · {t("score")} {c.score}%</p>
            <p className="cert-code">Code: <b>{c.code}</b></p>
            <p className="muted small">{t("issued")} {new Date(c.issued_at).toLocaleDateString()}</p>
            <button className="btn sm" onClick={() => window.print()}>🖨 Print / PDF</button>
          </div>
        ))}
      </div>

      <section className="card" style={{ marginTop: 22 }}>
        <h3>🔎 {t("verify")} a certificate</h3>
        <div className="row">
          <input className="input" style={{ maxWidth: 280 }} placeholder="TG-XXXXXXXXXX" value={verifyCode} onChange={(e) => setVerifyCode(e.target.value)} />
          <button className="btn" onClick={verify} disabled={!verifyCode.trim()}>{t("verify")}</button>
        </div>
        {verifyResult && (
          <p className={verifyResult.valid ? "success-text" : "error"} style={{ marginTop: 8 }}>
            {verifyResult.valid ? `✓ Genuine — ${verifyResult.title} (${verifyResult.score}%)` : "✗ No matching certificate."}
          </p>
        )}
      </section>
    </div>
  );
}
