"""Auto-grading for the item bank.

Every grader returns ``(correct: bool, awarded_fraction: float, feedback: str)``
where ``awarded_fraction`` is 0..1 of the item's points. Kinds that need a human
(``essay``) return ``needs_manual=True`` via :func:`grade_item`.
"""

import ast
import math
import operator
import re
import unicodedata

# ---------------------------------------------------------------------------
# Safe numeric/math evaluation (no ``eval`` of arbitrary code)
# ---------------------------------------------------------------------------

_ALLOWED_FUNCS = {
    "abs": abs, "round": round, "min": min, "max": max, "pow": pow,
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2,
    "log": math.log, "log10": math.log10, "exp": math.exp, "floor": math.floor,
    "ceil": math.ceil, "degrees": math.degrees, "radians": math.radians,
    "pi": math.pi, "e": math.e,
}
_BINOPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def safe_eval(expr):
    """Evaluate a math expression safely. Returns float, or None if invalid."""
    if expr is None:
        return None
    if isinstance(expr, (int, float)):
        return float(expr)
    s = str(expr).strip().replace("^", "**").replace("×", "*").replace("÷", "/")
    if not s:
        return None
    # Bare number?
    try:
        return float(s)
    except ValueError:
        pass
    try:
        tree = ast.parse(s, mode="eval")
    except SyntaxError:
        return None

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            return _BINOPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](ev(node.operand))
        if isinstance(node, ast.Name) and node.id in _ALLOWED_FUNCS:
            v = _ALLOWED_FUNCS[node.id]
            return float(v) if isinstance(v, (int, float)) else v
        if isinstance(node, ast.Call):
            fn = ev(node.func)
            if not callable(fn):
                raise ValueError("not callable")
            return fn(*[ev(a) for a in node.args])
        raise ValueError("unsupported expression")

    try:
        out = ev(tree)
        return float(out)
    except (ValueError, TypeError, ZeroDivisionError, OverflowError):
        return None


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _norm(text):
    """Casefold, strip accents/whitespace/punctuation for tolerant matching."""
    s = unicodedata.normalize("NFKD", str(text or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[.,;:!?'\"()]+$", "", s)
    return s


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


# ---------------------------------------------------------------------------
# Per-kind graders
# ---------------------------------------------------------------------------

def _grade_mcq(item, answer):
    expected = item.answer.get("value", item.answer.get("id"))
    got = answer.get("value", answer.get("id"))
    ok = _norm(expected) == _norm(got)
    return ok, 1.0 if ok else 0.0, ""


def _grade_multi(item, answer):
    expected = {_norm(x) for x in _as_list(item.answer.get("values", item.answer.get("value")))}
    got = {_norm(x) for x in _as_list(answer.get("values", answer.get("value")))}
    if not expected:
        return False, 0.0, ""
    if expected == got:
        return True, 1.0, ""
    # Partial credit: Jaccard, no credit for false positives beyond half.
    inter = len(expected & got)
    union = len(expected | got)
    frac = inter / union if union else 0.0
    return False, round(frac * 0.5, 3), "Partially correct."


def _grade_numeric(item, answer):
    expected = safe_eval(item.answer.get("value"))
    got = safe_eval(answer.get("value"))
    tol = float(item.answer.get("tolerance", 0) or 0)
    if expected is None or got is None:
        return False, 0.0, "Could not read a number."
    if tol == 0:
        tol = max(abs(expected) * 1e-6, 1e-9)
    ok = abs(got - expected) <= tol
    # Unit check (case-insensitive, ignoring spaces).
    exp_unit = _norm(item.answer.get("unit"))
    got_unit = _norm(answer.get("unit"))
    if ok and exp_unit and got_unit and exp_unit != got_unit:
        return False, 0.5, f"Right number, wrong unit (expected {item.answer.get('unit')})."
    return ok, 1.0 if ok else 0.0, "" if ok else "Not quite — check your calculation."


def _grade_math(item, answer):
    """Accept numerically-equivalent math expressions (x+1 vs 1+x won't match
    symbolically, but equal values will)."""
    expected = item.answer.get("value")
    got = answer.get("value")
    # Numeric equivalence at a sample point.
    if safe_eval(expected) is not None and safe_eval(got) is not None:
        a, b = safe_eval(expected), safe_eval(got)
        ok = abs(a - b) <= max(abs(a) * 1e-6, 1e-9)
        return ok, 1.0 if ok else 0.0, ""
    ok = _norm(expected) == _norm(got)
    return ok, 1.0 if ok else 0.0, ""


def _grade_code(item, answer):
    """Compare program output, ignoring trailing whitespace and line endings."""
    expected = (item.answer.get("expected_output") or "").strip().replace("\r\n", "\n")
    got = (answer.get("output") or "").strip().replace("\r\n", "\n")
    ok = expected == got
    return ok, 1.0 if ok else 0.0, "" if ok else "Output did not match."


def _grade_order(item, answer):
    expected = [_norm(x) for x in _as_list(item.answer.get("values"))]
    got = [_norm(x) for x in _as_list(answer.get("values"))]
    if expected == got:
        return True, 1.0, ""
    # Positional partial credit.
    if not expected:
        return False, 0.0, ""
    same = sum(1 for a, b in zip(expected, got) if a == b)
    return False, round(0.5 * same / len(expected), 3), "Some steps are out of order."


def _grade_match(item, answer):
    expected = {str(k): _norm(v) for k, v in (item.answer.get("pairs") or {}).items()}
    got = {str(k): _norm(v) for k, v in (answer.get("pairs") or {}).items()}
    if not expected:
        return False, 0.0, ""
    correct = sum(1 for k in expected if got.get(k) == expected[k])
    ok = correct == len(expected)
    return ok, (1.0 if ok else round(0.6 * correct / len(expected), 3)), ""


def _grade_short(item, answer):
    expected = _norm(item.answer.get("value"))
    got = _norm(answer.get("value"))
    if expected and expected == got:
        return True, 1.0, ""
    # Keyword-based fallback: all required keywords present.
    keywords = item.answer.get("keywords") or []
    if keywords:
        hits = sum(1 for k in keywords if _norm(k) in got)
        if hits == len(keywords):
            return True, 1.0, ""
        return False, round(0.5 * hits / len(keywords), 3), "Include the key ideas."
    return False, 0.0, ""


_GRADERS = {
    "mcq": _grade_mcq,
    "multi": _grade_multi,
    "numeric": _grade_numeric,
    "math": _grade_math,
    "code": _grade_code,
    "order": _grade_order,
    "match": _grade_match,
    "short": _grade_short,
}


def grade_item(item, answer):
    """Return dict: {correct, awarded (0..1), feedback, needs_manual}."""
    if item.kind in ("essay",):
        return {"correct": False, "awarded": 0.0, "feedback": "Awaiting teacher review.", "needs_manual": True}
    fn = _GRADERS.get(item.kind)
    if not fn:
        return {"correct": False, "awarded": 0.0, "feedback": "Unsupported item type.", "needs_manual": True}
    try:
        correct, awarded, feedback = fn(item, answer or {})
    except Exception:
        return {"correct": False, "awarded": 0.0, "feedback": "Could not grade this response.", "needs_manual": False}
    return {"correct": correct, "awarded": awarded, "feedback": feedback, "needs_manual": False}
