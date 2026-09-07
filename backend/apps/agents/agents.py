"""The AI agent roster.

Each agent wraps the pluggable LLM provider with a strict system prompt so
output stays age-appropriate, low-bandwidth and on-curriculum. Agents are also
*grouned*: the tutor retrieves snippets from the downloadable library so answers
reference real materials instead of floating.

- ContentAgent    : writes game-script lessons the frontend renderer can play.
- TutorAgent      : explains concepts conversationally, with history + context.
- GraderAgent     : scores free-text answers, returning score + stars + feedback.
- CurriculumAgent : plans the next step on a student's learning roadmap.
"""

import json
import logging

from django.utils import timezone
from django.conf import settings

from . import providers
from .models import AgentTask

logger = logging.getLogger(__name__)


SYSTEM_BASE = (
    "You are TazaGojo, an educational AI for students in low-resource regions. "
    "Respond in clear, simple language (ages 6-14). Be encouraging. "
    "Keep text SHORT (under 120 words). Never mention that you are a language model. "
)


def _retrieve_context(subject, question, limit=2):
    """Ground the tutor in the offline library: pull a short snippet from the
    most relevant free materials so answers point at real, downloadable study
    notes instead of floating abstractions."""
    try:
        from django.db.models import Q
        from apps.library.models import Material
    except Exception:  # library not migrated yet etc.
        return []
    terms = [t for t in question.lower().split() if len(t) > 3]
    qs = Material.objects.filter(active=True)
    if subject:
        qs = qs.filter(subject=subject)
    if terms:
        q = Q()
        for t in terms[:5]:
            q |= Q(title__icontains=t) | Q(description__icontains=t) | Q(outline__icontains=t)
        qs = qs.filter(q)
    out = []
    for m in qs.order_by("-downloads", "id")[:limit]:
        words = [w for w in terms if w in m.title.lower() or w in (m.description or "").lower()]
        outline = " ".join(m.outline or []) or re_plain(m.content or "")
        snippet = _plain(outline)[:280]
        out.append({"title": m.title, "snippet": snippet, "subject": subject})
    return out


def _plain(text):
    import re
    text = re.sub(r"<[^>]+>", " ", text or "")
    return " ".join(text.split())


def re_plain(text):
    return _plain(text)


class BaseAgent:
    kind = None

    def run(self, task: AgentTask) -> dict:
        raise NotImplementedError


class ContentAgent(BaseAgent):
    kind = AgentTask.Kind.GENERATE_LESSON

    SYSTEM = SYSTEM_BASE + (
        """You write lessons in STRICT JSON matching this schema exactly:
        {"title": str, "kind": "game", "xp": int, "content": {
          "engine": "catch|bubbles|sequencing|blockly",
          "instructions": str,
          "levels": [{"targets"|"problems"|"steps": [...], ...}]},
         "questions": [{"kind": "mcq", "prompt": str, "options": [str],
                        "answer": str, "hint": str}],
         "summary": str}. Grade level matters: keep it simple. Output ONLY the JSON, no prose."""
    )

    def run(self, task):
        course = task.course.name if task.course else "Math"
        level = task.input_data.get("grade_level", 3)
        topic = task.input_data.get("topic", "the basics")
        user_prompt = (
            f"Make a game-based {course} lesson for grade {level} about '{topic}' "
            "(no Internet jokes; offline-friendly, tiny data)."
        )
        text = providers.complete(self.SYSTEM, user_prompt)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            raise ValueError(f"Agent returned non-JSON: {text[:120]}")
        return data


def _pick_follow_ups(question):
    q = question.lower()
    if any(w in q for w in ("what", "why", "how", "?")):
        return [
            "Can you give me a simple example?",
            "What happens if I change the numbers?",
            "Show me a practice question like this.",
        ]
    return [
        "Why does that work?",
        "Could you give me one more example?",
        "What should I review before the next topic?",
    ]


class TutorAgent(BaseAgent):
    kind = AgentTask.Kind.TUTOR_REPLY

    SYSTEM = SYSTEM_BASE + (
        "You are a friendly tutor who ANSWERS WITH STEPS. Use examples from daily "
        "life the student knows: market, farm, phone, football, cooking. "
        "Guide with hints instead of giving the answer outright when it's homework. "
        "Return STRICT JSON: "
        '{"reply": str (your full answer, use "1." numbered lines), '
        '"follow_ups": [str, str, str] (3 short follow-up questions)}. '
        "Output ONLY the JSON, no prose."
    )

    def run(self, task):
        question = task.input_data.get("question", "")
        subject = task.input_data.get("subject", "")
        grade = task.input_data.get("grade_level")
        country = task.input_data.get("country", "")
        history = task.input_data.get("history", [])
        context = _retrieve_context(subject, question)

        ctx_blocks = []
        if context:
            ctx_blocks.append(
                "Relevant free study notes you can reference by title:\n"
                + "\n".join(f"- {c['title']}: {c['snippet']}" for c in context)
            )
        if history:
            ctx_blocks.append("Recent conversation (oldest last):\n" + "\n".join(history[-6:]))
        ctx = "\n".join(ctx_blocks)

        meta = f"Student background: grade {grade}, country {country}.\n" if grade or country else ""
        user_prompt = f"{meta}Subject: {subject or 'general'}\n{ctx}\n\nStudent asks: {question}"

        raw = providers.complete(self.SYSTEM, user_prompt)
        data = try_json(raw)
        if isinstance(data, dict) and data.get("reply"):
            data.setdefault("follow_ups", _pick_follow_ups(question))
            data["context"] = [c["title"] for c in context[:2]]
            return data
        return {"reply": raw or "Let's try that again with a simpler step.", "follow_ups": _pick_follow_ups(question)}


class GraderAgent(BaseAgent):
    kind = AgentTask.Kind.GRADE

    SYSTEM = SYSTEM_BASE + (
        """You grade short free-text answers. Return STRICT JSON:
        {"score": float 0-1, "stars": int 1-3,
         "feedback": str (one short sentence)}.
        Be kind, be specific about what was right, and what to fix. Output ONLY JSON."""
    )

    def run(self, task):
        prompt = task.input_data.get("prompt", "")
        expected = task.input_data.get("expected", "")
        answer = task.input_data.get("answer", "")
        user_prompt = (
            f"Question: {prompt}\\nCorrect answer: {expected}\\n"
            f"Student answered: {answer}\\nGrade it."
        )
        text = providers.complete(self.SYSTEM, user_prompt)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            auto = 1.0 if str(expected).strip().lower() in str(answer).strip().lower() else 0.3
            data = {"score": auto, "stars": 3 if auto > 0.9 else 1,
                    "feedback": "Keep practicing and try again!"}
        return data


class CurriculumAgent(BaseAgent):
    kind = AgentTask.Kind.PLAN_CURRICULUM

    SYSTEM = SYSTEM_BASE + (
        "You are a curriculum planner on a school whose library has free study "
        "notes for math, english, science and computing. Given a student's goals "
        "and progress, recommend ONE concrete next step with a reason, and point "
        "to a free topic/resource. Return STRICT JSON: "
        '{"plan": str (1-3 sentences), "next_topic": str, "resource": str}. '
        "Output ONLY JSON."
    )

    def run(self, task):
        goals = task.input_data.get("goals", []) or []
        progress = task.input_data.get("progress", "") or ""
        weak = task.input_data.get("weaknesses", "") or ""
        g = " ".join(f"{x.get('goal','')}" for x in goals)
        user_prompt = (
            f"Learning goals: {g or 'improve broadly'}. Progress: {progress} "
            f"Weak areas: {weak}. What is the next step?"
        )
        raw = providers.complete(self.SYSTEM, user_prompt)
        data = try_json(raw)
        if isinstance(data, dict) and data.get("plan"):
            return data
        return {"plan": raw, "next_topic": g or "Continue your current plan", "resource": "Library → your subject"}


def try_json(raw):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Model wrapped JSON in markdown fences; extract the first {...}.
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                return None
        return None


AGENTS = {a.kind: a for a in (ContentAgent(), TutorAgent(), GraderAgent(), CurriculumAgent())}


def run_task(task: AgentTask) -> AgentTask:
    """Execute one queued task synchronously."""
    agent = AGENTS[task.kind]
    task.status = AgentTask.Status.RUNNING
    task.save(update_fields=["status"])
    try:
        task.output_data = agent.run(task)
        task.status = AgentTask.Status.DONE
    except Exception as e:  # noqa: BLE001
        logger.exception("agent task %s failed", task.pk)
        task.status = AgentTask.Status.FAILED
        task.error = str(e)[:500]
    task.finished_at = timezone.now()
    task.save(update_fields=["output_data", "status", "error", "finished_at"])
    return task