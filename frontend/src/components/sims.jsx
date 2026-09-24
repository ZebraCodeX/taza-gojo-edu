// components/sims.jsx — offline interactive science/electronics simulations.
//
// Pure SVG + React, no canvas libs and no network: they run on a low-end phone
// with no signal. Each sim calls onChange(state) so a lab's browser-side tests
// can be evaluated against real simulated state.

import React, { useEffect, useMemo, useRef, useState } from "react";

/* ------------------------------ DC circuit ------------------------------ */

export function CircuitSim({ assets = {}, onChange }) {
  const [voltage, setVoltage] = useState(6);
  const [resistance, setResistance] = useState(assets.resistance || 3);
  const [closed, setClosed] = useState(false);
  const current = closed ? voltage / Math.max(resistance, 0.1) : 0;
  const bulbLit = current > 0.05;

  useEffect(() => {
    onChange?.({ current: Number(current.toFixed(3)), voltage, resistance, bulb_lit: bulbLit });
  }, [current, voltage, resistance, bulbLit]);

  const glow = Math.min(1, current / 2);
  return (
    <div className="sim">
      <svg viewBox="0 0 320 180" className="sim-svg" role="img" aria-label="DC circuit">
        <rect x="1" y="1" width="318" height="178" rx="12" className="sim-bg" />
        {/* wires */}
        <path d="M40 40 H280 V140 H40 Z" fill="none" className="wire" />
        {/* battery */}
        <g transform="translate(150,40)">
          <line x1="-14" y1="0" x2="-14" y2="26" className="wire" />
          <line x1="14" y1="0" x2="14" y2="26" className="wire" />
          <line x1="-22" y1="0" x2="-6" y2="0" className="wire" />
          <line x1="6" y1="0" x2="22" y2="0" className="wire" />
          <text x="0" y="-8" textAnchor="middle" className="sim-label">{voltage} V</text>
        </g>
        {/* switch */}
        <g transform="translate(70,40)">
          <circle cx="0" cy="0" r="3" className="node" />
          <circle cx="34" cy="0" r="3" className="node" />
          <line x1="0" y1="0" x2={closed ? 34 : 24} y2={closed ? 0 : -16} className="wire" />
          <text x="17" y="22" textAnchor="middle" className="sim-label">switch</text>
        </g>
        {/* resistor */}
        <g transform="translate(230,90)">
          <rect x="-20" y="-10" width="40" height="20" rx="3" className="comp" />
          <text x="0" y="4" textAnchor="middle" className="sim-label sm">{resistance} Ω</text>
        </g>
        {/* bulb */}
        <g transform="translate(70,140)">
          <circle cx="0" cy="0" r="16" className="bulb" style={{ filter: `drop-shadow(0 0 ${12 * glow}px #ffd54a)`, opacity: 0.35 + 0.65 * glow }} />
          <text x="0" y="30" textAnchor="middle" className="sim-label">bulb</text>
        </g>
        <text x="160" y="172" textAnchor="middle" className="sim-readout">
          I = {current.toFixed(2)} A{bulbLit ? " · bulb lit" : ""}
        </text>
      </svg>
      <div className="sim-controls">
        <label>Voltage <input type="range" min="0" max="12" step="0.5" value={voltage} onChange={(e) => setVoltage(+e.target.value)} /> <b>{voltage} V</b></label>
        <label>Resistance <input type="range" min="1" max="20" step="0.5" value={resistance} onChange={(e) => setResistance(+e.target.value)} /> <b>{resistance} Ω</b></label>
        <button className={"btn sm " + (closed ? "primary" : "")} onClick={() => setClosed((c) => !c)}>
          {closed ? "Open switch" : "Close switch"}
        </button>
      </div>
    </div>
  );
}

/* ------------------------------- Pendulum ------------------------------- */

export function PendulumSim({ assets = {}, onChange }) {
  const [length, setLength] = useState(1.0); // metres
  const [angle, setAngle] = useState(0.35);
  const raf = useRef(0);
  const state = useRef({ t: 0, a: 0.35 });

  const period = useMemo(() => 2 * Math.PI * Math.sqrt(length / 9.81), [length]);

  useEffect(() => {
    let last = performance.now();
    const loop = (now) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      state.current.t += dt;
      const omega = Math.sqrt(9.81 / length);
      state.current.a = angle * Math.cos(omega * state.current.t);
      setAngle(state.current.a);
      raf.current = requestAnimationFrame(loop);
    };
    raf.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf.current);
  }, [length]);

  useEffect(() => {
    onChange?.({ length, period: Number(period.toFixed(2)), period_increases_with_length: true });
  }, [length, period]);

  const px = 160 + Math.sin(angle) * (60 + length * 60);
  const py = 20 + Math.cos(angle) * (60 + length * 60);
  return (
    <div className="sim">
      <svg viewBox="0 0 320 220" className="sim-svg" role="img" aria-label="Pendulum">
        <rect x="1" y="1" width="318" height="218" rx="12" className="sim-bg" />
        <line x1="160" y1="20" x2={px} y2={py} className="wire" />
        <circle cx="160" cy="20" r="3" className="node" />
        <circle cx={px} cy={py} r="12" className="bob" />
        <text x="160" y="210" textAnchor="middle" className="sim-readout">Period ≈ {period.toFixed(2)} s</text>
      </svg>
      <div className="sim-controls">
        <label>Length <input type="range" min="0.3" max="1.6" step="0.1" value={length} onChange={(e) => setLength(+e.target.value)} /> <b>{length.toFixed(1)} m</b></label>
      </div>
    </div>
  );
}

/* ----------------------------- Water cycle ------------------------------ */

export function WaterCycleSim({ assets = {}, onChange }) {
  const [temp, setTemp] = useState(20);
  const rain = temp >= 60;
  useEffect(() => {
    onChange?.({ temperature: temp, rain_observed: rain, evaporated: temp > 40 });
  }, [temp, rain]);
  const evap = Math.max(0, (temp - 20) / 80);
  return (
    <div className="sim">
      <svg viewBox="0 0 320 200" className="sim-svg" role="img" aria-label="Water cycle">
        <rect x="1" y="1" width="318" height="198" rx="12" className="sim-bg" />
        <circle cx="60" cy="45" r={12 + temp / 6} className="sun" />
        <path d="M60 70 Q160 30 250 70" fill="none" className="wire dashed" opacity={0.3 + evap} />
        <rect x="40" y="160" width="240" height="24" rx="4" className="water" />
        <text x="160" y="176" textAnchor="middle" className="sim-label sm">water</text>
        {evap > 0.2 && <text x="150" y="110" className="sim-label sm" opacity={Math.min(1, evap)}>💧 evaporation</text>}
        {rain && <text x="200" y="120" className="sim-label">🌧 precipitation</text>}
        <text x="160" y="30" textAnchor="middle" className="sim-readout">Temperature {temp}°C</text>
      </svg>
      <div className="sim-controls">
        <label>Sun / heat <input type="range" min="0" max="100" step="1" value={temp} onChange={(e) => setTemp(+e.target.value)} /> <b>{temp}°C</b></label>
      </div>
    </div>
  );
}

export function Sim({ assets, onChange }) {
  switch (assets?.sim) {
    case "dc-circuit": return <CircuitSim assets={assets} onChange={onChange} />;
    case "pendulum": return <PendulumSim assets={assets} onChange={onChange} />;
    case "water-cycle": return <WaterCycleSim assets={assets} onChange={onChange} />;
    default:
      return <p className="muted">This simulation is coming soon. Read the instructions above and continue.</p>;
  }
}
