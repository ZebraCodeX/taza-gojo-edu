// pages/ReaderPage.jsx — read a cached material fully offline, or fetch it when
// online. Opens straight from IndexedDB when the network is gone.

import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { materialStore } from "../services/offline";
import { sanitizeHtml } from "../util/sanitize";

export default function ReaderPage() {
  const { id } = useParams();
  const [mat, setMat] = useState(null);
  const [err, setErr] = useState("");
  const [mode, setMode] = useState("loading"); // loading | offline | online

  useEffect(() => {
    (async () => {
      const cached = await materialStore.get(id);
      if (cached?.content) {
        setMat(cached);
        setMode("offline");
        return;
      }
      try {
        const { data } = await api.get(`/api/v1/library/materials/${id}/`);
        setMat(data);
        setMode("online");
        await materialStore.save(data.id, data); // next time it opens offline
      } catch {
        if (cached) {
          setMat(cached);
          setMode("offline");
        } else {
          setErr("This material isn't saved on this device and you're offline.");
        }
      }
    })();
  }, [id]);

  if (!mat && !err) return <p className="loading">Opening…</p>;
  if (err) return <p className="error center mt">{err}</p>;

  const body = mat.content ? sanitizeHtml(mat.content) : "<p>No offline body available — open the original source instead.</p>";

  return (
    <div className="reader">
      <div className="row between">
        <Link className="btn sm" to="/library">← Library</Link>
        <span className={`pill ${mode === "online" ? "" : "offline"}`}>
          {mode === "online" ? "Read online" : "Read offline"}
        </span>
      </div>
      <h1>{mat.title}</h1>
      <p className="muted small">{mat.provider} · {mat.license_note} · {mat.grade_band}</p>
      {mat.url && (
        <a className="btn sm" href={mat.url} target="_blank" rel="noopener noreferrer">
          Open original source ↗
        </a>
      )}
      <div className="card prose" dangerouslySetInnerHTML={{ __html: body }} />
    </div>
  );
}