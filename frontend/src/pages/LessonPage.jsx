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
      {lesson.lecture_url && (
        <section className="card lecture">
          <div className="row between">
            <div>
              <h2>🎬 Video lecture</h2>
              <p className="muted small">
                {lesson.lecture_duration ? `${lesson.lecture_duration}s · ` : ""}Watch first, then play the game.
              </p>
            </div>
            <span className="pill">low-data ~{lesson.lecture_duration ? Math.max(1, Math.round(lesson.lecture_duration * 0.05)) : 2} MB</span>
          </div>
          <video className="lecture-video" controls preload="metadata" playsInline>
            <source src={lesson.lecture_url} type="video/mp4" />
            Your device can't play this video; the game below works offline too.
          </video>
        </section>
      )}
      <GameRenderer lesson={lesson} onDone={(r) => setResult(r)} />
      {result && <div className="card success">Well done, {result.stars}/3 stars! {result.stars === 3 ? "Perfect — syncing your progress…" : "Progress saved — syncing…"}</div>}
    </div>
  );
}