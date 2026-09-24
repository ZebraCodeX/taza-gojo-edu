// lessons/InteractiveLesson.jsx — Brilliant-style guided-discovery engine.
//
// A lesson is a sequence of steps. Learners manipulate (sliders, plots,
// circuits), answer, get immediate feedback with the *reason why*, reveal a
// hint or a worked solution, then continue. Everything runs client-side so a
// lesson plays with zero signal; progress is reported through onDone.

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useI18n } from "../i18n";
import { CircuitSim } from "../components/sims";
import { track } from "../services/events";

/* ------------------------------ scoring ------------------------------ */

function shuffle(arr, seed) {
  const a = [...arr];
  let s = seed;
  for (let i = a.length - 1; i > 0; i--) {
    s = (s * 9301 + 49297) % 233280;
    const j = Math.floor((s / 233280) * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function initialValue(step) {
  if (!step) return null;
  switch (step.type) {
    case "multi": return [];
    case "match": return {};
    case "order": {
      // Shuffle but never start already solved.
      let s = shuffle(step.items || [], (step.items?.length || 3) * 7 + 13);
      if (JSON.stringify(s) === JSON.stringify(step.items)) s = [...s].reverse();
      return s;
    }
    case "slider": return step.min ?? 0;
    case "numeric": return "";
    default: return null;
  }
}

function isReady(step, v) {
  switch (step.type) {
    case "concept": return true;
    case "mcq": return v !== null && v !== undefined;
    case "multi": return (v || []).length > 0;
    case "numeric": return String(v ?? "").trim() !== "";
    case "slider": return true;
    case "order": return (v || []).length === (step.items || []).length;
    case "match": return Object.keys(v || {}).length === (step.left || []).length;
    case "plot": return v !== null && v !== undefined;
    case "circuit": return true;
    case "free": return String(v ?? "").trim().length >= 12;
    default: return true;
  }
}

function evaluate(step, v) {
  switch (step.type) {
    case "concept": return true;
    case "mcq": return v === (step.options || []).findIndex((o) => o.correct);
    case "multi": {
      const key = (step.options || []).map((o, i) => (o.correct ? i : -1)).filter((i) => i >= 0).sort();
      return JSON.stringify([...(v || [])].sort()) === JSON.stringify(key);
    }
    case "numeric": {
      const n = Number(v);
      return Number.isFinite(n) && Math.abs(n - Number(step.answer)) <= (step.tolerance || 0) + 1e-9;
    }
    case "slider":
      return Math.abs(Number(v) - Number(step.target)) <= (step.tolerance || 0) + 1e-9;
    case "order":
      return JSON.stringify(v) === JSON.stringify(step.items);
    case "match":
      return Object.entries(step.pairs || {}).every(([k, val]) => v?.[k] === val);
    case "plot": {
      if (v === null || v === undefined) return false;
      if (step.mode === "numberline") return Math.abs(Number(v) - Number(step.target)) <= (step.max - step.min) * 0.06;
      return Math.hypot(v[0] - step.target[0], v[1] - step.target[1]) <= Math.max(2, (step.max - step.min) * 0.1);
    }
    case "circuit":
      return Math.abs(Number(v) - Number(step.target_current)) <= 0.2;
    case "free":
      return String(v ?? "").trim().length >= 12;
    default:
      return true;
  }
}

/* ------------------------------ visuals ------------------------------ */

function StepVisual({ step, value }) {
  const v = step.value;
  if (step.visual === "fraction") {
    const parts = Math.max(1, Number(value) || 1);
    return (
      <div className="il-visual" aria-hidden>
        <div className="fraction-bar">
          {Array.from({ length: parts }).map((_, i) => (
            <div key={i} className={"fraction-part" + (i === 0 ? " on" : "")} />
          ))}
        </div>
        <div className="il-visual-cap">1 part of {parts} · 1/{parts}</div>
      </div>
    );
  }
  if (step.visual === "balance") {
    const x = Number(value) || 0;
    const diff = (x + 3) - 11;
    const tilt = Math.max(-10, Math.min(10, diff * 1.5));
    return (
      <div className="il-visual" aria-hidden>
        <div className="balance" style={{ transform: `rotate(${tilt}deg)` }}>
          <div className="pan"><span>x + 3 = {x + 3}</span></div>
          <div className="beam" />
          <div className="pan"><span>11</span></div>
        </div>
        <div className="il-visual-cap">{diff === 0 ? "Balanced! ⚖️" : diff > 0 ? "Left side is heavier" : "Right side is heavier"}</div>
      </div>
    );
  }
  if (step.visual === "force") {
    const pct = Math.min(1, (Number(value) || 0) / (step.max || 10));
    return (
      <div className="il-visual" aria-hidden>
        <div className="force-row">
          <div className="force-arrow" style={{ width: `${10 + pct * 80}%` }} />
          <span className="force-ball">⚽</span>
        </div>
        <div className="il-visual-cap">Force = {Number(value) || 0} {step.unit || "N"}</div>
      </div>
    );
  }
  if (step.visual === "battery") {
    return <div className="il-visual" aria-hidden><div className="il-visual-emoji">🔋</div><div className="il-visual-cap">{Number(value) || 0} V</div></div>;
  }
  return <div className="il-visual" aria-hidden><div className="il-visual-emoji">{step.visual || "💡"}</div></div>;
}

/* ------------------------------ step views ------------------------------ */

function PlotStep({ step, value, setValue, disabled }) {
  const ref = useRef(null);
  const max = step.max ?? 25;
  const min = step.min ?? 0;
  const place = (e) => {
    if (disabled) return;
    const r = ref.current.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width;
    const py = 1 - (e.clientY - r.top) / r.height;
    if (step.mode === "numberline") {
      setValue(Math.max(min, Math.min(max, min + px * (max - min))));
    } else {
      setValue([Math.round(px * max), Math.round(py * max)]);
    }
  };
  return (
    <div className="plot" ref={ref} onPointerDown={place} role="button" tabIndex={0} aria-label="Interactive graph">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="plot-svg">
        {step.mode === "xy" && Array.from({ length: 6 }).map((_, i) => (
          <g key={i}>
            <line x1={(i * 100) / 5} y1="0" x2={(i * 100) / 5} y2="100" className="grid-line" />
            <line x1="0" y1={(i * 100) / 5} x2="100" y2={(i * 100) / 5} className="grid-line" />
          </g>
        ))}
        {step.mode === "numberline" ? (
          <>
            <line x1="0" y1="50" x2="100" y2="50" className="axis" />
            {value !== null && value !== undefined && (
              <circle cx={((value - min) / (max - min)) * 100} cy="50" r="4" className="marker" />
            )}
          </>
        ) : (
          value && <circle cx={(value[0] / max) * 100} cy={100 - (value[1] / max) * 100} r="4" className="marker" />
        )}
      </svg>
      <div className="il-visual-cap">
        {step.mode === "numberline"
          ? value !== null && value !== undefined ? `Your mark: ${Number(value).toFixed(2)}` : "Tap the line to place your mark"
          : value ? `Your point: (${value[0]}, ${value[1]})` : "Tap the graph to place your point"}
      </div>
    </div>
  );
}

function OrderStep({ step, value, setValue, disabled }) {
  const list = value || [];
  const move = (i, dir) => {
    const j = i + dir;
    if (j < 0 || j >= list.length) return;
    const a = [...list];
    [a[i], a[j]] = [a[j], a[i]];
    setValue(a);
  };
  return (
    <ol className="il-order">
      {list.map((item, i) => (
        <li key={item}>
          <span className="il-order-num">{i + 1}</span>
          <span className="il-order-txt">{item}</span>
          <span className="il-order-btns">
            <button className="icon-btn sm" disabled={disabled || i === 0} onClick={() => move(i, -1)} aria-label="Move up">▲</button>
            <button className="icon-btn sm" disabled={disabled || i === list.length - 1} onClick={() => move(i, 1)} aria-label="Move down">▼</button>
          </span>
        </li>
      ))}
    </ol>
  );
}

function StepView({ step, value, setValue, disabled }) {
  switch (step.type) {
    case "concept":
      return (
        <div className="il-concept">
          <StepVisual step={step} value={value} />
          <h2 className="il-title">{step.title}</h2>
          <p className="il-body">{step.body}</p>
        </div>
      );
    case "mcq":
      return (
        <div className="opts">
          {(step.options || []).map((o, i) => (
            <button key={i} disabled={disabled} className={"opt" + (value === i ? " on" : "")} onClick={() => setValue(i)}>
              {o.text}
            </button>
          ))}
        </div>
      );
    case "multi": {
      const sel = value || [];
      const toggle = (i) => {
        const s = new Set(sel);
        s.has(i) ? s.delete(i) : s.add(i);
        setValue([...s]);
      };
      return (
        <div className="opts">
          {(step.options || []).map((o, i) => (
            <button key={i} disabled={disabled} className={"opt" + (sel.includes(i) ? " on" : "")} onClick={() => toggle(i)}>
              {o.text}
            </button>
          ))}
        </div>
      );
    }
    case "numeric":
      return (
        <div className="row">
          <input className="input" inputMode="decimal" placeholder="Your answer" disabled={disabled}
            value={value ?? ""} onChange={(e) => setValue(e.target.value)} />
          {step.unit && <span className="il-unit">{step.unit}</span>}
        </div>
      );
    case "slider":
      return (
        <div>
          <StepVisual step={step} value={value} />
          <input className="il-slider" type="range" min={step.min} max={step.max} step={step.step || 1}
            value={value ?? step.min} disabled={disabled} onChange={(e) => setValue(Number(e.target.value))} />
          <div className="il-slider-cap">{value} {step.unit}</div>
        </div>
      );
    case "order":
      return <OrderStep step={step} value={value} setValue={setValue} disabled={disabled} />;
    case "match":
      return (
        <div className="match-grid">
          {(step.left || []).map((l) => (
            <div className="match-row" key={l}>
              <span className="match-left">{l}</span>
              <select className="input" disabled={disabled} value={value?.[l] || ""}
                onChange={(e) => setValue({ ...(value || {}), [l]: e.target.value })}>
                <option value="">— choose —</option>
                {(step.right || []).map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
          ))}
        </div>
      );
    case "plot":
      return <PlotStep step={step} value={value} setValue={setValue} disabled={disabled} />;
    case "circuit":
      return <CircuitSim assets={{ sim: "dc-circuit", resistance: step.resistance || 3 }} onChange={(s) => setValue(s.current)} />;
    case "free":
      return (
        <div>
          <textarea className="ta" rows={4} disabled={disabled} value={value ?? ""}
            onChange={(e) => setValue(e.target.value)} placeholder="Write your answer in your own words…" />
        </div>
      );
    default:
      return <p className="muted">Unsupported step.</p>;
  }
}

/* ------------------------------ main ------------------------------ */

export default function InteractiveLesson({ lesson, onDone }) {
  const { t } = useI18n();
  const steps = useMemo(() => lesson?.content?.steps || [], [lesson]);
  const [idx, setIdx] = useState(0);
  const [value, setValue] = useState(() => initialValue(steps[0]));
  const [phase, setPhase] = useState("work"); // work | feedback | done
  const [correct, setCorrect] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [results, setResults] = useState([]);
  const [summary, setSummary] = useState(null);
  const started = useRef(Date.now());

  const step = steps[idx];

  useEffect(() => {
    setValue(initialValue(steps[idx]));
    setPhase("work");
    setCorrect(false);
    setShowHint(false);
  }, [idx, steps]);

  useEffect(() => {
    track("lesson_start", { subject: lesson?.subject, object_type: "lesson", object_id: lesson?.id, metadata: { engine: "interactive" } });
  }, [lesson?.id]);

  if (!step) return <p className="muted">This lesson has no steps yet.</p>;

  const gradable = step.type !== "concept";
  const canCheck = isReady(step, value);

  const check = () => {
    if (!canCheck) return;
    const ok = evaluate(step, value);
    setCorrect(ok);
    setResults((r) => [...r, { type: step.type, ok }]);
    setPhase("feedback");
  };

  const advance = () => {
    if (idx + 1 < steps.length) setIdx(idx + 1);
    else finish([...results, gradable ? { type: step.type, ok: correct } : { type: step.type, ok: true }]);
  };

  const finish = (all) => {
    const scored = all.filter((r) => r.type !== "concept");
    const total = scored.length || 1;
    const right = scored.filter((r) => r.ok).length;
    const pct = right / total;
    const stars = pct >= 0.9 ? 3 : pct >= 0.7 ? 2 : 1;
    const out = { stars, score: Math.round(pct * 100), correct: right, total, xp: lesson?.xp || 20 };
    setSummary(out);
    setPhase("done");
    track("lesson_complete", { subject: lesson?.subject, object_type: "lesson", object_id: lesson?.id, value: out.score, metadata: { engine: "interactive" } });
    onDone?.(out);
  };

  if (phase === "done" && summary) {
    return (
      <div className="card il-done">
        <div className="il-done-seal">{summary.stars === 3 ? "🏆" : summary.stars === 2 ? "🎉" : "💪"}</div>
        <h2>Lesson complete</h2>
        <p className="il-done-score">{summary.score}%</p>
        <p className="muted">{summary.correct} of {summary.total} correct · +{summary.xp} XP</p>
        <div className="stars" aria-label={`${summary.stars} of 3 stars`}>{"★".repeat(summary.stars)}{"☆".repeat(3 - summary.stars)}</div>
        <button className="btn primary" onClick={() => { setIdx(0); setResults([]); setSummary(null); setPhase("work"); }}>
          Try again
        </button>
      </div>
    );
  }

  const pct = Math.round(((idx + (phase === "feedback" ? 1 : 0)) / steps.length) * 100);
  const chosenWhy = step.type === "mcq" && value !== null ? step.options?.[value]?.why : null;

  return (
    <div className="interactive">
      <div className="il-top">
        <div className="il-progress"><div className="il-progress-bar" style={{ width: `${pct}%` }} /></div>
        <span className="muted small">{idx + 1}/{steps.length}</span>
        {step.hint && <button className="linkbtn" onClick={() => setShowHint((v) => !v)}>{showHint ? "Hide hint" : "💡 Hint"}</button>}
      </div>

      <div className="card il-card">
        {step.type !== "concept" && <p className="q-prompt">{step.prompt}</p>}
        {showHint && step.hint && <p className="hint il-hint">💡 {step.hint}</p>}
        <StepView step={step} value={value} setValue={setValue} disabled={phase === "feedback"} />
      </div>

      {phase === "feedback" && (
        <div className={"card feedback " + (correct ? "ok" : "bad")} aria-live="polite">
          <b>{correct ? "✓ Correct" : "Not quite — here's why"}</b>
          {!correct && chosenWhy && <p>{chosenWhy}</p>}
          {!correct && step.type === "numeric" && <p>The answer is <b>{step.answer} {step.unit || ""}</b>.</p>}
          {!correct && step.type === "slider" && <p>The target was <b>{step.target} {step.unit || ""}</b>.</p>}
          {step.explain && <p className="muted small">{step.explain}</p>}
          {step.type === "free" && step.model && (
            <div className="il-model"><b>Model answer</b><p>{step.model}</p></div>
          )}
          <button className="btn primary" onClick={advance}>{idx + 1 < steps.length ? "Continue →" : "Finish"}</button>
        </div>
      )}

      {phase === "work" && (
        <button className="btn primary block" disabled={!canCheck} onClick={check}>
          {step.type === "concept" ? "Got it" : "Check"}
        </button>
      )}
    </div>
  );
}
