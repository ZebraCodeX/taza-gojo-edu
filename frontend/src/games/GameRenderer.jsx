// games/GameRenderer.jsx — interprets the tiny JSON "game scripts" the content
// agents produce. Four engines exist today; the schema is additive so new ones
// ship without app updates:
//
//   catch     -> letters/objects fall; tap the correct target
//   bubbles   -> a problem shows; pop the bubble with the right answer
//   sequencing-> tap the steps in the correct order
//   blockly   -> build a command list so the mascot reaches the goal
//
// Each engine runs entirely offline (no assets, no network) and hands progress
// to the offline sync queue.

import React, { useEffect, useMemo, useRef, useState } from "react";
import { reportProgress } from "../services/offline";

export default function GameRenderer({ lesson, onDone }) {
  const script = lesson.content || {};
  return (
    <div className="game">
      <h2>{lesson.title}</h2>
      <p className="hint">{script.instructions}</p>
      {script.engine === "catch" && <CatchEngine script={script} lesson={lesson} onDone={onDone} />}
      {script.engine === "bubbles" && <BubblesEngine script={script} lesson={lesson} onDone={onDone} />}
      {script.engine === "sequencing" && <SequenceEngine script={script} lesson={lesson} onDone={onDone} />}
      {script.engine === "blockly" && <BlocklyEngine script={script} lesson={lesson} onDone={onDone} />}
      {!script.engine && (
        <div className="card">
          <p>Lesson content is loading…</p>
          <button className="btn primary" onClick={() => onDone && onDone()}>Mark done</button>
        </div>
      )}
    </div>
  );
}

function finished(lesson, stars, onDone) {
  reportProgress(lesson.id, { completed: true, score: stars * 10, stars });
  if (onDone) onDone({ stars });
}

function Stars({ n }) {
  return <span className="stars">{"★".repeat(n)}{"☆".repeat(3 - n)}</span>;
}

function Cage({ children }) {
  return <div className="game-arena">{children}</div>;
}

/* ---------------- catch: tap the falling letter that matches ---------------- */

function CatchEngine({ script, lesson, onDone }) {
  const [level, setLevel] = useState(0);
  const [items, setItems] = useState([]);
  const [score, setScore] = useState(0);
  const cfg = script.levels[level] || script.levels[0];
  const targets = cfg?.targets || [];

  useEffect(() => {
    if (!targets.length) return;
    let alive = true;
    const spawn = () => {
      const pick = () => targets[Math.floor(Math.random() * targets.length)];
      const correct = pick();
      const isTarget = Math.random() < 0.5;
      setItems((prev) => [
        ...prev.slice(-8),
        { id: Math.random().toString(36).slice(2), v: isTarget ? correct : pick(), kind: isTarget ? "ok" : "bad" },
      ]);
    };
    spawn();
    const iv = setInterval(() => {
      if (!alive) return;
      setItems((prev) => prev.map((i) => ({ ...i, y: (i.y || 0) + 18 })).filter((i) => (i.y || 0) < 300));
      spawn();
    }, 700);
    return () => {
      alive = false;
      clearInterval(iv);
    };
  }, [level, targets]);

  const tap = (item) => {
    if (item.kind === "ok") {
      setScore((s) => s + 1);
      setItems((p) => p.filter((i) => i.id !== item.id));
      if (score + 1 >= cfg.rounds) {
        const repeat = lesson.content.levels.length > level + 1 ? () => setLevel((l) => l + 1) : null;
        if (repeat) {
          setScore(0);
          repeat();
        } else {
          finished(lesson, 3, onDone);
        }
      }
    } else {
      setItems((p) => p.filter((i) => i.id !== item.id));
    }
  };

  return (
    <Cage>
      <div className="scoreboard">Score: {score} / {cfg.rounds} · Level {level + 1}</div>
      <div style={{ position: "relative" }}>
        {items.map((i) => (
          <button key={i.id} className="fall" style={{ top: i.y || 0, left: 20 + Math.random() * 70 + "%" }} onClick={() => tap(i)}>
            {i.v}
          </button>
        ))}
      </div>
    </Cage>
  );
}

/* ------------------ bubbles: pop the correct sum/product ------------------- */

function BubblesEngine({ script, lesson, onDone }) {
  const [level, setLevel] = useState(0);
  const [score, setScore] = useState(0);
  const cfg = script.levels[level] || script.levels[0];
  const [problem, setProblem] = useState(cfg.problems[0]);
  const [idx, setIdx] = useState(0);

  const a = problem[0];
  const b = problem[1];

  const bubbles = useMemo(() => {
    const correct = a + b;
    const options = new Set([correct]);
    while (options.size < 3) options.add(correct + Math.ceil(Math.random() * 5 + 1));
    return [...options].sort(() => Math.random() - 0.5);
  }, [a, b]);

  const tap = (v) => {
    if (v === a + b) {
      setScore((s) => s + 1);
      if (idx + 1 >= cfg.problems.length) {
        if (lesson.content.levels.length > level + 1) {
          setLevel((l) => l + 1);
          setIdx(0);
          setScore(0);
        } else {
          finished(lesson, 3, onDone);
        }
      } else {
        setIdx((i) => i + 1);
        setProblem(cfg.problems[idx + 1]);
      }
    }
  };

  useEffect(() => {
    setProblem(cfg.problems[0]);
    setIdx(0);
  }, [level, cfg]);

  return (
    <Cage>
      <div className="problem">{a} + {b} = ?</div>
      <div className="scoreboard">Solved: {score}</div>
      <div className="bubbles">
        {bubbles.map((v) => (
          <button key={v} className="bubble" onClick={() => tap(v)}>{v}</button>
        ))}
      </div>
    </Cage>
  );
}

/* ------------------- sequencing: tap the steps in order -------------------- */

function SequenceEngine({ script, lesson, onDone }) {
  const steps = script.levels?.[0]?.steps || [];
  const [picked, setPicked] = useState([]);

  const tap = (step) => {
    if (picked.includes(step)) return;
    if (step === steps[picked.length]) {
      const next = [...picked, step];
      setPicked(next);
      if (next.length === steps.length) finished(lesson, 3, onDone);
    } else {
      setPicked([]); // wrong order: reset
    }
  };

  return (
    <Cage>
      <div className="scoreboard">Tap the steps in order</div>
      <div className="steps">
        {[...steps].sort(() => Math.random() - 0.5).map((s, i) => (
          <button
            key={s + i}
            className={picked.includes(s) ? "step done" : "step"}
            onClick={() => tap(s)}
          >
            {s} {picked.includes(s) ? "✓" : ""}
          </button>
        ))}
      </div>
      <Stars n={Math.floor((picked.length / steps.length) * 3) || 0} />
    </Cage>
  );
}

/* ------------------ blockly-lite: build commands to goal ------------------- */

const WH = 300;
function BlocklyEngine({ script, lesson, onDone }) {
  const cfg = script.levels?.[0] || {};
  const goal = cfg.goal; // e.g. "3,1"
  const [commands, setCommands] = useState([]);
  const [pos, setPos] = useState([0, 0]);
  const [tried, setTried] = useState(false);

  const run = () => {
    let [x, y] = [0, 0];
    for (const c of commands) {
      if (c === "forward") y = Math.max(0, y + 1);
      if (c === "turn_right") x = Math.min(cfg.grid - 1, x + 1);
    }
    setPos([x, y]);
    setTried(true);
    if (goal && `${x},${y}` === goal) finished(lesson, 3, onDone);
  };

  return (
    <Cage>
      <div className="grid" style={{ width: WH, height: WH }} onClick={() => setTried(false)}>
        {Array.from({ length: cfg.grid * cfg.grid }).map((_, i) => {
          const cx = i % cfg.grid;
          const cy = Math.floor(i / cfg.grid);
          return (
            <div
              key={i}
              className={
                "cell" +
                (cx === pos[0] && cy === pos[1] ? " mascot" : "") +
                (goal && `${cx},${cy}` === goal ? " goal" : "")
              }
            />
          );
        })}
      </div>
      <div className="commands">
        {["forward", "turn_right", "turn_left"].map((c) => (
          <button key={c} className="cmd" onClick={() => setCommands((p) => [...p, c])}>
            {c.replace("_", " ")}
          </button>
        ))}
        <button className="btn primary" onClick={run}>Run ▶</button>
        <button className="btn" onClick={() => setCommands([])}>Clear</button>
      </div>
      {commands.length > 0 && (
        <div className="blocklist">{commands.map((c, i) => <span key={i}>{c.replace("_", " ")}</span>)}</div>
      )}
      {tried && goal && `${pos[0]},${pos[1]}` !== goal && (
        <p className="error">Not quite — check your commands!</p>
      )}
    </Cage>
  );
}