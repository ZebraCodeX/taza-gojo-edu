# Interactive lessons (Brilliant-style)

Lessons of `kind: "interactive"` store a **step script** in `Lesson.content` and
are rendered by `frontend/src/lessons/InteractiveLesson.jsx`. They are built for
guided discovery: learners manipulate something, answer, get immediate feedback
with the reason, reveal a hint or worked solution, then continue. Everything is
client-side, so a lesson plays with zero signal.

## Step schema

```json
{
  "engine": "interactive",
  "steps": [
    { "type": "concept", "visual": "⚡", "title": "...", "body": "..." },
    { "type": "mcq",     "prompt": "...", "options": [{"text":"...","correct":true,"why":"..."}], "hint": "...", "explain": "..." },
    { "type": "multi",   "prompt": "...", "options": [{"text":"...","correct":true}], "explain": "..." },
    { "type": "numeric", "prompt": "...", "answer": 5, "tolerance": 0.01, "unit": "m/s²", "hint": "...", "explain": "..." },
    { "type": "slider",  "visual": "force", "min": 0, "max": 20, "step": 1, "target": 12, "unit": "N", "hint": "...", "explain": "..." },
    { "type": "order",   "prompt": "...", "items": ["...", "..."], "explain": "..." },
    { "type": "match",   "prompt": "...", "left": ["..."], "right": ["..."], "pairs": {"a":"b"} },
    { "type": "plot",    "mode": "numberline|xy", "prompt": "...", "target": 0.75, "min": 0, "max": 1 },
    { "type": "circuit", "prompt": "...", "target_current": 2.0, "resistance": 3 },
    { "type": "free",    "prompt": "...", "model": "model answer", "hint": "..." }
  ]
}
```

Visuals for sliders: `fraction`, `balance`, `force`, `battery`, or any emoji.

## Scoring

Graded steps (everything except `concept`) count toward the score. Stars: 3 at
≥90%, 2 at ≥70%, else 1. Completion reports `{stars, score, correct, total, xp}`
through `onDone`, which the lesson page turns into offline progress + analytics
events.

## Authoring

Content lives in `backend/apps/courses/interactive_content.py`; load it with:

```bash
python manage.py seed_interactive
```

Seeded lessons: fractions, solving equations, forces & motion, distance-time
graphs, Ohm's law, series vs parallel circuits, and variables & loops. Add a
lesson by appending to `LESSONS` — no frontend change required unless you
introduce a new step type.
