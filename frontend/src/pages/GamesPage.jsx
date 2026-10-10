// pages/GamesPage.jsx — the Game Arcade: every educational game in one place.
//
// Games are grouped by engine (catch, bubbles, sequencing, blockly, shop) so a
// child can pick a play style they like and still learn the same subject. The
// page reads the offline lesson cache first, then refreshes from the API, so it
// opens instantly and still lists games with zero signal.

import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useStore } from "../store/app";
import { local } from "../services/offline";
import { useI18n } from "../i18n";

// Engine catalogue: label, icon and a one-line "how to play" for each play style.
const ENGINES = {
  catch: { label: "Catch", icon: "🪣", color: "#2ea44f", blurb: "Tap the falling answer before it drops." },
  bubbles: { label: "Bubbles", icon: "🫧", color: "#2563eb", blurb: "Pop the bubble with the right answer." },
  sequencing: { label: "Sequencing", icon: "🔢", color: "#8957e5", blurb: "Put the steps in the correct order." },
  blockly: { label: "Blockly", icon: "🧩", color: "#1f6feb", blurb: "Build a command list to reach the goal." },
  shop: { label: "Shop", icon: "🛒", color: "#d29922", blurb: "Tap coins to pay the exact price." },
  interactive: { label: "Interactive", icon: "✨", color: "#db2777", blurb: "Discover ideas with sliders and plots." },
};
const OTHER = { label: "Arcade", icon: "🎮", color: "#6d28d9", blurb: "Playful practice." };

const engineKey = (content) => (content?.engine && ENGINES[content.engine] ? content.engine : "other");
const engineMeta = (key) => (key === "other" ? OTHER : ENGINES[key]);

function toRow(lesson, course, moduleTitle) {
  const content = lesson.content || {};
  return {
    id: lesson.id,
    title: lesson.title,
    xp: lesson.xp || 0,
    duration: lesson.duration_minutes || 5,
    instructions: content.instructions || engineMeta(engineKey(content)).blurb,
    engine: engineKey(content),
    course: course ? { slug: course.slug, name: course.name, icon: course.icon, color: course.color } : null,
    moduleTitle: moduleTitle || "",
  };
}

export default function GamesPage() {
  const { t } = useI18n();
  const online = useStore((s) => s.online);
  const [games, setGames] = useState([]);
  const [progress, setProgress] = useState({});
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [partial, setPartial] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      const cached = await local.all("lessons").catch(() => []);
      const cachedById = new Map(cached.map((l) => [l.id, l]));

      // Offline baseline: whatever lessons are saved on this device.
      const offlineGames = cached
        .filter((l) => l.content?.engine || l.kind === "game")
        .map((l) => toRow(l, null, ""));
      if (alive && offlineGames.length) setGames(offlineGames);

      try {
        const listRes = await api.get("/api/v1/courses/");
        const courses = Array.isArray(listRes.data) ? listRes.data : listRes.data?.results || [];

        const catalogs = await Promise.all(
          courses.map((c) =>
            api
              .get(`/api/v1/courses/${c.slug}/catalog/`)
              .then((r) => ({ course: c, modules: Array.isArray(r.data) ? r.data : [] }))
              .catch(() => null)
          )
        );

        const rows = [];
        for (const cat of catalogs) {
          if (!cat) continue;
          for (const mod of cat.modules) {
            for (const l of mod.lessons || []) {
              if (l.kind === "game" || l.kind === "interactive") rows.push({ lesson: l, course: cat.course, mod });
            }
          }
        }

        // Resolve each game's engine: prefer the device cache, else fetch detail.
        const detailed = await Promise.all(
          rows.map(async ({ lesson, course, mod }) => {
            const cachedLesson = cachedById.get(lesson.id);
            if (cachedLesson?.content?.engine) return toRow({ ...lesson, content: cachedLesson.content }, course, mod.title);
            try {
              const { data } = await api.get(`/api/v1/courses/lessons/${lesson.id}/`);
              return toRow({ ...lesson, content: data.content || {} }, course, mod.title);
            } catch {
              return toRow(lesson, course, mod.title);
            }
          })
        );

        if (alive) {
          setGames(detailed);
          setPartial(false);
        }
      } catch {
        if (alive) setPartial(true);
      }

      // Completed games (accurate when online; best-effort otherwise).
      try {
        const { data } = await api.get("/api/v1/courses/progress/");
        const rows = Array.isArray(data) ? data : data?.results || [];
        const map = {};
        for (const p of rows) map[p.lesson] = p;
        if (alive) setProgress(map);
      } catch { /* offline — no progress badge */ }

      if (alive) setLoading(false);
    })();
    return () => { alive = false; };
  }, [online]);

  const stats = useMemo(() => {
    const subjects = new Set(games.map((g) => g.course?.slug).filter(Boolean));
    const engines = new Set(games.map((g) => g.engine));
    const done = games.filter((g) => progress[g.id]?.completed).length;
    const xp = games.reduce((n, g) => n + g.xp, 0);
    return { total: games.length, subjects: subjects.size, engines: engines.size, done, xp };
  }, [games, progress]);

  const counts = useMemo(() => {
    const c = {};
    for (const g of games) c[g.engine] = (c[g.engine] || 0) + 1;
    return c;
  }, [games]);

  const groups = useMemo(() => {
    const order = [...Object.keys(ENGINES), "other"];
    const byEngine = new Map();
    for (const g of games) {
      if (filter !== "all" && g.engine !== filter) continue;
      if (!byEngine.has(g.engine)) byEngine.set(g.engine, []);
      byEngine.get(g.engine).push(g);
    }
    return order.filter((k) => byEngine.has(k)).map((k) => [k, byEngine.get(k)]);
  }, [games, filter]);

  const chipKeys = useMemo(() => groups.map(([k]) => k), [groups]);

  return (
    <div className="arcade">
      <section className="arcade-hero">
        <div>
          <h1>🎮 {t("games")}</h1>
          <p className="arcade-sub">
            Every learning game in one place. Pick a game, play it offline, and earn
            stars and XP while you practise.
          </p>
          <div className="row">
            <Link className="btn primary" to={games[0] ? `/lesson/${games[0].id}` : "/dashboard"}>
              ▶ Play a game
            </Link>
            <Link className="btn ghost" to="/library">📚 Browse resources</Link>
          </div>
        </div>
        <div className="arcade-hero-art">🏆</div>
      </section>

      <div className="stat-cards">
        <div className="stat-card"><span className="sc-ico">🎮</span><span><span className="sc-num">{stats.total}</span><span className="sc-label">games</span></span></div>
        <div className="stat-card"><span className="sc-ico">🧩</span><span><span className="sc-num">{stats.engines}</span><span className="sc-label">game types</span></span></div>
        <div className="stat-card"><span className="sc-ico">⚡</span><span><span className="sc-num">{stats.xp}</span><span className="sc-label">XP to earn</span></span></div>
        <div className="stat-card"><span className="sc-ico">✅</span><span><span className="sc-num">{stats.done}</span><span className="sc-label">completed</span></span></div>
      </div>

      <div className="chips arcade-chips">
        <button className={"chip" + (filter === "all" ? " on" : "")} onClick={() => setFilter("all")}>
          All · {games.length}
        </button>
        {chipKeys.map((k) => {
          const m = engineMeta(k);
          return (
            <button key={k} className={"chip" + (filter === k ? " on" : "")} onClick={() => setFilter(k)}>
              {m.icon} {m.label} · {counts[k] || 0}
            </button>
          );
        })}
      </div>

      {partial && <p className="error small">Offline — showing games saved on this device.</p>}

      {groups.map(([key, list]) => {
        const m = engineMeta(key);
        return (
          <section key={key} className="arcade-group">
            <div className="section-head">
              <h2>{m.icon} {m.label}</h2>
              <span className="muted small">{m.blurb}</span>
            </div>
            <div className="grid arcade-grid">
              {list.map((g) => {
                const done = progress[g.id]?.completed;
                const stars = progress[g.id]?.stars || 0;
                const cover = g.course?.color || m.color;
                return (
                  <Link to={`/lesson/${g.id}`} key={g.id} className={"card arcade-card" + (done ? " done" : "")}>
                    <div className="arcade-thumb" style={{ background: `linear-gradient(135deg, ${m.color}, ${cover})` }}>
                      <span className="arcade-emoji">{m.icon}</span>
                      <span className="arcade-subj">{g.course?.icon || "🎮"}</span>
                      {done && <span className="arcade-tick">✅</span>}
                    </div>
                    <div className="arcade-body">
                      <h3>{g.title}</h3>
                      <div className="arcade-meta">
                        <span className="badge kind">{m.label}</span>
                        {g.course?.name && <span className="badge">{g.course.name}</span>}
                      </div>
                      <p className="muted small arcade-inst">{g.instructions}</p>
                      <div className="row between arcade-foot">
                        <span className="muted small">{g.duration} min · +{g.xp} XP</span>
                        {done
                          ? <span className="arcade-stars">{"★".repeat(stars)}{"☆".repeat(3 - stars)}</span>
                          : <span className="arcade-play">Play ▶</span>}
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          </section>
        );
      })}

      {!loading && games.length === 0 && (
        <div className="empty card">
          <span className="e-ico">🎮</span>
          <b>No games saved yet</b>
          <p className="muted">Connect to download the game lessons, then play offline.</p>
        </div>
      )}
      {loading && games.length === 0 && <p className="muted">Loading games…</p>}
    </div>
  );
}
