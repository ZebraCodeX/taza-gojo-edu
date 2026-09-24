// pages/LivePage.jsx — live classes (1:1 and groups up to 15).
//
// Media is carried by a self-hosted LiveKit SFU. The LiveKit client is loaded
// lazily from a configurable CDN URL; if the server has no LiveKit keys the
// page explains the P2P fallback instead of failing.

import React, { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { useI18n } from "../i18n";
import { useStore } from "../store/app";
import { track } from "../services/events";
import PageHeader from "../components/PageHeader";
import Empty from "../components/Empty";

const LIVEKIT_CLIENT =
  (typeof window !== "undefined" && window.LIVEKIT_CLIENT_URL) ||
  "https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.esm.mjs";

const SUBJECT_ICON = { physics: "🧲", electricity: "⚡", math: "🧮", science: "🔬", computing: "💻", english: "📖" };

export default function LivePage() {
  const { t } = useI18n();
  const role = useStore((s) => s.user?.user?.role || "student");
  const canHost = role === "teacher" || role === "admin";
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");
  const [active, setActive] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const load = async () => {
    try {
      const { data } = await api.get("/api/v1/live/classes/");
      setRows(Array.isArray(data) ? data : data.results || []);
    } catch {
      setErr("Couldn't load live classes.");
    }
  };
  useEffect(() => { load(); }, []);

  const create = async (e) => {
    e.preventDefault();
    const f = e.target;
    try {
      await api.post("/api/v1/live/classes/", {
        title: f.title.value,
        subject: f.subject.value,
        scheduled_at: f.when.value || undefined,
        max_participants: Number(f.cap.value) || 15,
      });
      f.reset();
      setShowForm(false);
      load();
    } catch {
      setErr("Could not schedule the class.");
    }
  };

  if (active) return <LiveRoom live={active} onLeave={() => setActive(null)} />;

  return (
    <div>
      <PageHeader
        icon="🎥"
        title={t("liveClasses")}
        subtitle="Face-to-face classes tuned for low bandwidth. Groups up to 15."
        actions={canHost && <button className="btn primary sm" onClick={() => setShowForm((v) => !v)}>{showForm ? "Cancel" : "+ Schedule"}</button>}
      />

      {showForm && canHost && (
        <form className="card" onSubmit={create} style={{ marginBottom: 16 }}>
          <h3>Schedule a class</h3>
          <div className="row">
            <input className="input" name="title" placeholder="Class title" required style={{ flex: "2 1 220px" }} />
            <select className="input" name="subject" defaultValue="physics" style={{ flex: "1 1 130px" }}>
              {["physics", "electricity", "math", "science", "computing"].map((s) => (
                <option key={s} value={s}>{SUBJECT_ICON[s]} {s}</option>
              ))}
            </select>
            <input className="input" name="when" type="datetime-local" style={{ flex: "1 1 190px" }} />
            <input className="input unit" name="cap" type="number" min="2" max="15" defaultValue="15" />
            <button className="btn primary">Create</button>
          </div>
        </form>
      )}

      {err && <p className="error">{err}</p>}
      {rows.length === 0 && !err && (
        <Empty icon="🎥" title="No classes scheduled yet" text={canHost ? "Schedule your first live class above." : "Your teacher's classes will appear here."} />
      )}
      <div className="grid courses">
        {rows.map((c) => (
          <div className="card course" key={c.id}>
            <div className="course-thumb" style={{ background: "var(--primary-soft)", color: "var(--primary)" }}>
              <span>{SUBJECT_ICON[c.subject] || "🎥"}</span>
            </div>
            <div className="row between" style={{ margin: "0 14px" }}>
              <span className={"pill" + (c.status === "live" ? " live" : " soft")}>{c.status}</span>
              <span className="muted small">{c.attendee_count}/{c.max_participants}</span>
            </div>
            <h3 style={{ marginTop: 6 }}>{c.title}</h3>
            <p className="muted small" style={{ margin: "0 14px" }}>{new Date(c.scheduled_at).toLocaleString()}</p>
            <p className="muted small" style={{ margin: "0 14px 10px" }}>Host: {c.host_name} · {c.duration_minutes} min</p>
            <div style={{ margin: "auto 14px 14px" }}>
              <button className="btn primary block" onClick={() => setActive(c)}>🎥 {t("join")}</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function LiveRoom({ live, onLeave }) {
  const { t } = useI18n();
  const [status, setStatus] = useState("connecting");
  const [err, setErr] = useState("");
  const localRef = useRef(null);
  const remoteRef = useRef(null);
  const roomRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      let join;
      try {
        const { data } = await api.post(`/api/v1/live/classes/${live.id}/join/`);
        join = data;
        track("live_join", { subject: live.subject, object_type: "live", object_id: live.id });
      } catch {
        setErr("Could not join the class.");
        setStatus("error");
        return;
      }
      if (!join.configured || !join.token) {
        setStatus("fallback");
        return;
      }
      try {
        const LK = await import(/* @vite-ignore */ LIVEKIT_CLIENT);
        const room = new LK.Room({ adaptiveStream: true, dynacast: true });
        roomRef.current = room;
        room
          .on(LK.RoomEvent.TrackSubscribed, (track) => {
            if (track.kind === "video" && remoteRef.current) track.attach(remoteRef.current);
            else if (track.kind === "audio") track.attach();
          })
          .on(LK.RoomEvent.Disconnected, () => !cancelled && setStatus("ended"));
        await room.connect(join.url, join.token);
        if (join.can_publish) {
          await room.localParticipant.enableCameraAndMicrophone();
          room.localParticipant.videoTrackPublications.forEach((pub) => {
            if (pub.videoTrack && localRef.current) pub.videoTrack.attach(localRef.current);
          });
        }
        if (!cancelled) setStatus("live");
      } catch {
        setErr("Live video couldn't start on this device.");
        setStatus("error");
      }
    })();
    return () => {
      cancelled = true;
      roomRef.current?.disconnect?.();
      api.post(`/api/v1/live/classes/${live.id}/leave/`).catch(() => {});
    };
  }, [live.id]);

  return (
    <div className="call">
      <div className="call-bar">
        <span className="pill">{live.title}</span>
        <span className={"pill " + (status === "live" ? "live" : "soft")}>{status}</span>
        <button className="btn sm" onClick={onLeave}>← {t("back")}</button>
      </div>

      {status === "fallback" && (
        <div className="card lobby">
          <h3>LiveKit isn't configured on this server yet</h3>
          <p className="muted small">
            Set <code>LIVEKIT_URL</code>, <code>LIVEKIT_API_KEY</code> and <code>LIVEKIT_API_SECRET</code> to enable
            group video. Until then, 1:1 sessions use the built-in peer-to-peer tutoring call.
          </p>
        </div>
      )}

      {(status === "live" || status === "connecting") && (
        <div className="call-frames">
          <video ref={remoteRef} className="remote" autoPlay playsInline />
          <video ref={localRef} className="local" autoPlay playsInline muted />
        </div>
      )}
      {status === "connecting" && <p className="hint">🔌 Connecting to the class…</p>}
      {err && <p className="error">{err}</p>}
    </div>
  );
}
