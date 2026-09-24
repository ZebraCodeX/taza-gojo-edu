# Labs

Hands-on coding, circuit, physics and science labs that run **on the device**.
No server execution (per the product decision), so labs work with zero signal
after the app shell is cached.

## Coding (browser-only)

- **JavaScript** runs in a sandboxed **Web Worker** (no DOM, 5-second timeout),
  capturing `console.log`. Fully offline.
- **Python** runs through **Pyodide** (WebAssembly), loaded lazily from a
  configurable URL (`window.PYODIDE_URL`). For true offline Python, vendor
  Pyodide into the PWA cache and point `PYODIDE_URL` at it.
- **Blockly** is used for the primary-age block lab.

Tests (`lab.tests`) ship to the client and are evaluated there:

```json
[{ "name": "prints Hello, World!", "expected_output": "Hello, World!" }]
```

The server keeps the authoritative definition and derives `passed` from the
reported per-test results, so a client can't assert success without evidence.

## Circuits / electronics

`frontend/src/components/sims.jsx` implements an SVG **DC circuit** simulator
(battery, switch, resistor, bulb) with live current readout — `I = V / R`. Used
by the series-circuit and Ohm's-law labs. Tests use `expr` assertions:

```json
[{ "name": "current is 2 A", "expr": "current", "expected": 2.0 }]
```

## Physics / science

- **Pendulum** sim (length → period), test `period_increases_with_length`.
- **Water cycle** sim (heat → evaporation → rain), test `rain_observed`.

## Lab runner

`GET /api/v1/labs/labs/?kind=circuit` then `POST /api/v1/labs/labs/<slug>/submit/`
with `{code, language, results:[{name, passed}]}`. Submissions are stored per
user and contribute to analytics.

## Seed

```bash
python manage.py seed_labs   # 8 labs across coding/circuit/physics/science
```
