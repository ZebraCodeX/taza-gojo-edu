# Taza-Gojo EDU — AI agents

The school is *run* by AI agents rather than a fixed authored static site:

- **ContentAgent** writes lessons (game scripts), quizzes and hints per topic.
- **GraderAgent** scores free-text answers and gives encouraging, age-appropriate
  feedback.
- **CurriculumAgent** sequences courses/modules and reads a student's profile to
  reorder or add remedial lessons.
- **TutorAgent** powers `/api/v1/agents/tutor/ask/` — a one-shot tutor that replies
  in steps and plain language, tuned for young learners.

## How work flows

```
HTTP API ──► AgentTask(rendered) ──► Redis-less polling in run_agents ──► provider ──► result
                 ▲                      │
                 └── Conversation / Message persisted (student history)
```

1. A view (e.g. `TutorAskView`, or a content writer script) enqueues an
   `AgentTask` with `agent`, `prompt` (actually a few-shot instruction), `input`.
2. the `run_agents` management command polls (`status=new`) in a loop, calls the
   configured provider, writes the structured result back, and marks `done`/`failed`.
3. Result data lands where the caller expects: a `Message` for chat, or a draft
   `Lesson` the content team can approve.

The task queue is deliberately dependency-light: it poll's the DB like a worker
(watchdog-friendly, one less service to run on a school's own server). Swap in
Redis-backed tasks or Celery later without changing the enqueue API.

## Providers (`agents/providers.py`)

Set `AI_PROVIDER` — one of:

| Provider | Config | Use |
|---|---|---|
| `mock` (default) | none | Local dev/tests; returns canned answers proving the plumbing, never hits the network |
| `openai` | `AI_API_KEY` | Production remote |
| `ollama` | `AI_API_URL` (e.g. `http://localhost:11434`) | School-owned model server on the LAN |

Calls are one-shot with the following hints in the instruction block: *"You are
a patient tutor for a 9-year-old. Use short sentences. No jargon. End with one
practice question."* Providers raise `ProviderError` on unreachable endpoints so
the queue marks the task `failed` and the client can retry. The tutor is exposed
at `POST /api/v1/agents/tutor/ask/`; the frontend calls it as an assist inside
lessons rather than as a standalone chat page.

## Lesson content format (what ContentAgent emits)

`Lesson.content` is a **game script**, rendered by `frontend/src/games/GameRenderer.jsx`:

```json
{
  "engine": "bubbles",
  "instructions": "Pop the bubble with the right answer.",
  "levels": [
    { "problems": [[3, 4], [5, 2], [8, 7]] },
    { "problems": [[12, 9], [7, 6]] }
  ]
}
```

Engines: `catch` (tap correct falling object), `bubbles` (pop correct sum),
`sequencing` (order steps), `blockly` (build an algorithm). New engines are added
to the renderer without touching the backend or shipping an app update.

## Security & honesty

- Agents never see another student's data; prompts are rendered from the task
  only.
- Mock provider makes the full pipeline inspectable offline — important because
  schools on this program often run the stack without any outside connectivity.
- `run_agents` retries with exponential backoff and exposes `failed` tasks; no
  prompt content is logged.