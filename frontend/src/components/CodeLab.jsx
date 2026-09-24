// components/CodeLab.jsx — browser-only code execution.
//
// JavaScript runs in a sandboxed Web Worker (no DOM, 5s timeout) so it works
// completely offline. Python runs through Pyodide (WebAssembly). Pyodide is
// loaded lazily from a configurable URL; production builds should vendor it
// into the PWA cache (see docs/offline-first.md) for true offline Python.

import React, { useEffect, useState } from "react";
import { useI18n } from "../i18n";

const PYODIDE_URL =
  (typeof window !== "undefined" && window.PYODIDE_URL) ||
  "https://cdn.jsdelivr.net/pyodide/v0.26.2/full/pyodide.js";

let pyodidePromise = null;

async function getPyodide() {
  if (pyodidePromise) return pyodidePromise;
  pyodidePromise = (async () => {
    if (!window.loadPyodide) {
      await import(/* @vite-ignore */ PYODIDE_URL);
    }
    return window.loadPyodide({ indexURL: PYODIDE_URL.replace(/pyodide\.js$/, "") });
  })();
  return pyodidePromise;
}

function runJS(code) {
  return new Promise((resolve) => {
    const src = `
      let out = [];
      self.console = { log: (...a) => out.push(a.map(String).join(' ')), error: (...a) => out.push(a.map(String).join(' ')) };
      self.onmessage = (e) => {
        try { (0, eval)(e.data); self.postMessage({ ok: true, output: out.join('\\n') }); }
        catch (err) { self.postMessage({ ok: false, output: out.join('\\n'), error: String(err) }); }
      };
    `;
    const url = URL.createObjectURL(new Blob([src], { type: "text/javascript" }));
    const worker = new Worker(url);
    let done = false;
    const finish = (r) => { if (!done) { done = true; resolve(r); worker.terminate(); } };
    worker.onmessage = (e) => finish(e.data);
    worker.onerror = (e) => finish({ ok: false, output: "", error: e.message || "Runtime error" });
    worker.postMessage(code);
    setTimeout(() => finish({ ok: false, output: "", error: "Timed out after 5s (check for an infinite loop)." }), 5000);
  });
}

async function runPython(code) {
  const py = await getPyodide();
  let out = "";
  py.setStdout({ batched: (s) => { out += s + "\n"; } });
  py.setStderr({ batched: (s) => { out += s + "\n"; } });
  try {
    await py.runPythonAsync(code);
    return { ok: true, output: out.replace(/\n$/, "") };
  } catch (err) {
    return { ok: false, output: out.replace(/\n$/, ""), error: String(err.message || err) };
  }
}

export default function CodeLab({ lab, onChange }) {
  const { t } = useI18n();
  const [code, setCode] = useState(lab.starter_code || "");
  const [output, setOutput] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState([]);

  useEffect(() => { setCode(lab.starter_code || ""); setResults([]); setOutput(""); setError(""); }, [lab.id]);

  const evaluate = (out) => {
    const tests = (lab.tests || []).filter((x) => "expected_output" in x);
    return tests.map((tc) => ({
      name: tc.name || "test",
      passed: (out || "").trim() === String(tc.expected_output).trim(),
    }));
  };

  const run = async () => {
    setBusy(true);
    setError("");
    try {
      let res;
      if (lab.language === "python") res = await runPython(code);
      else res = await runJS(code);
      setOutput(res.output || "");
      if (res.error) setError(res.error);
      const evaluated = evaluate(res.output);
      setResults(evaluated);
      onChange?.({ results: evaluated, code, output: res.output, error: res.error || "" });
    } catch (e) {
      setError(
        lab.language === "python"
          ? "Python needs a one-time download (Pyodide). Connect once to enable offline Python."
          : String(e.message || e)
      );
      setResults([]);
      onChange?.({ results: [], code, output: "", error: String(e.message || e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="codelab">
      <textarea
        className="code-input"
        spellCheck={false}
        value={code}
        onChange={(e) => setCode(e.target.value)}
        rows={Math.max(6, code.split("\n").length + 1)}
        aria-label="Code editor"
      />
      <div className="row">
        <button className="btn primary" onClick={run} disabled={busy}>{busy ? "Running…" : `▶ ${t("run")}`}</button>
        <span className="muted small">{lab.language === "python" ? "Python" : "JavaScript"} · runs on your device</span>
      </div>
      {output && (
        <pre className="code-output" aria-live="polite">{output}</pre>
      )}
      {error && <p className="error small">{error}</p>}
      {results.length > 0 && (
        <ul className="test-list">
          {results.map((r, i) => (
            <li key={i} className={r.passed ? "pass" : "fail"}>{r.passed ? "✓" : "✗"} {r.name}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
