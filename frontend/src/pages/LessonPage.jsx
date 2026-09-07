// pages/LessonPage.jsx — loads (or reuses cached) lesson detail and hands it to
// the game renderer. Caches lesson JSON into IndexedDB for true offline play.

import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import GameRenderer from "../games/GameRenderer";
import { api } from "../api/client";
import { local } from "../services/offline";

export default function LessonPage() {
  const { id } = useParams();
  const [lesson, setLesson] = useState(null);
  const [err, setErr] = useState("");
  const [result, setResult] = useState(null);

  useEffect(() => {
    (async () => {
      // Offline fast-path first, then freshen from the network.
      const cached = await local.get("lessons", Number(id));
      if (cached) setLesson(cached);
      try {
        const { data } = await api.get(`/api/v1/courses/lessons/${id}/`);
        setLesson(data);
        await local.put("lessons", { id: Number(id), ...data });
      } catch {
        if (!cached) setErr("This lesson isn't cached and you're offline.");
      }
    })();
  }, [id]);

  if (!lesson && !err) return <p>Loading lesson…</p>;
  if (err && !lesson) return <p className="error">{err}</p>;

  return (
    <div>
      <GameRenderer lesson={lesson} onDone={(r) => setResult(r)} />
      {result && <div className="card success">Well done! <strong>{result.stars} stars!+3 stars</strong> syncing…</div>}
    </div>
  );
}