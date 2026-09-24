"""Pluggable LLM providers.

Kept dependency-light: raw HTTP calls so the backend runs anywhere, including a
school's single Raspberry Pi that doubles as a local Ollama server. The `mock`
provider lets the whole system run with zero network access (demo/testing).
"""

import json
import re
from django.conf import settings

import requests


class ProviderError(RuntimeError):
    pass


def _headers():
    return {"Content-Type": "application/json"}


def openai_complete(system, user):
    key = settings.AI_API_KEY
    if not key:
        raise ProviderError("AI_API_KEY not configured")
    r = requests.post(
        f"{settings.AI_OPENAI_URL}/chat/completions",
        headers={**_headers(), "Authorization": f"Bearer {key}"},
        json={
            "model": settings.AI_MODEL,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.6,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def ollama_complete(system, user):
    r = requests.post(
        f"{settings.AI_API_URL}/api/chat",
        headers=_headers(),
        json={
            "model": settings.AI_MODEL,
            "stream": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def _mock_math(expr):
    """Tiny deterministic math engine for the mock tutor so it genuinely
    solves arithmetic (sums, products, percentages) step by step."""
    import re
    expr = expr.lower().replace(",", "")
    expr = expr.strip()
    # "what is N% of M"
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)\b", expr)
    if m:
        p, n = float(m.group(1)), float(m.group(2))
        val = p / 100.0 * n
        return {
            "reply": f"1. Percent means 'out of 100'. So {p:g}% is {p:g} out of every 100.\n"
                     f"2. Multiply: {p:g} ÷ 100 = {p/100:g}.\n"
                     f"3. Then {p/100:g} × {n:g} = {val:g}.\n"
                     f"So {p:g}% of {n:g} is {val:g}.",
            "follow_ups": ["What is 10% of 250?", "How do I find a discount of 25%?", "Why divide by 100 first?"],
        }
    m = re.search(r"(\d+(?:\.\d+)?)\s*([+\-*x×÷/])\s*(\d+(?:\.\d+)?)\s*=?\s*[.?]?$", expr)
    if m:
        a, op, b = float(m.group(1)), m.group(2), float(m.group(3))
        ops = {"+": ("add", a + b), "-": ("subtract", a - b),
               "*": ("multiply", a * b), "x": ("multiply", a * b), "×": ("multiply", a * b),
               "/": ("divide", a / b), "÷": ("divide", a / b)}
        name, val = ops[op]
        return {
            "reply": f"1. We need to {name} {a:g} and {b:g}.\n2. {a:g} {op} {b:g} = {val:g}.\n"
                     f"So the answer is {val:g}. Try one more on your own!",
            "follow_ups": [f"What is {b:g} {op} {a:g}?", "Show a word problem for this.", "Now round our answer to 2 decimals."],
        }
    return None


def _mock_context(subject, question):
    """Default tutor path: ground the answer in the free study library."""
    try:
        from django.db.models import Q
        from apps.library.models import Material
        terms = [t for t in re.findall(r"[a-z]{4,}", question.lower())]
        qs = Material.objects.filter(active=True)
        if subject:
            qs = qs.filter(subject=subject)
        if terms:
            q = Q()
            for t in terms[:5]:
                q |= Q(title__icontains=t) | Q(description__icontains=t)
            qs = qs.filter(q)
        mat = qs.order_by("-downloads", "id").first()
    except Exception:
        mat = None
    if mat:
        return (
            f'1. You are studying "{mat.title}" — that is exactly the right level.\n'
            f'2. Start with this from your notes: {mat.description[:140]}\n'
            f"3. Try the practice ideas at the bottom of that material in the Library.\n"
            f"4. Still stuck? Tell me the exact sentence or number that confuses you."
        )
    return (
        "1. Let's take it one step at a time — can you re-tell me the question in your own words?\n"
        "2. Underline the key numbers or keywords, then we solve it together.\n"
        "3. After that I'll give you one like it to practise."
    )


def mock_complete(system, user):
    """A genuinely helpful deterministic tutor (no network needed) so the system
    works everywhere, and so demos never sound robotic."""
    q = user.lower()
    if "lessons in strict json" in system.lower():
        return (
            '{"title": "Fractions Adventure", "kind": "game", "content": '
            '{"engine": "bubbles", "instructions": "Pop the bubble with the correct fraction.", '
            '"levels": [{"problems": [[1,2],[1,4],[2,3]]}]}}'
        )
    if "grade short free-text" in system.lower():
        return json.dumps({"score": 0.85, "stars": 3,
                           "feedback": "Good effort! Check your units next time."})
    if "curriculum planner" in system.lower():
        return json.dumps({"plan": "Practise your weakest topic for 15 minutes today, then "
                                    "try one question from next week's material.",
                           "next_topic": "Your weakest subject's next unit",
                           "resource": "Library → your subject"})
    # Tutor: solve math if possible, otherwise answer from the library context.
    math = _mock_math(q)
    if math:
        return json.dumps(math)
    match = re.search(r"(?:subject|Context|Student background)[:\s]+([a-z]+)", q)
    subject = match.group(1) if match else ""
    return json.dumps({
        "reply": _mock_context(subject, q),
        "follow_ups": [
            "Can you give me a simple example?",
            "What happens if I change the numbers?",
            "Show me a practice question like this.",
        ],
    })


def complete(system, user, provider=None):
    p = provider or settings.AI_PROVIDER
    fn = {
        "openai": openai_complete,
        "ollama": ollama_complete,
        "mock": mock_complete,
    }.get(p)
    if fn is None:
        raise ProviderError(f"Unknown AI_PROVIDER={p!r}")
    try:
        return fn(system, user)
    except ProviderError:
        raise
    except Exception as e:
        # Degrade gracefully: never fail the classroom because the model is down.
        return mock_complete(system, user) if p != "mock" else (_raise(e))


def _raise(e):
    raise ProviderError(str(e)) from e