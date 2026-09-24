"""SMS + USSD quiz logic, reusing the assessment item bank and grader."""

from apps.assessment import grading
from apps.assessment.models import Item

from .models import PhoneUser, QuizSession, Message, Channel

SUBJECTS = [
    ("math", "Math"),
    ("english", "English"),
    ("science", "Science"),
    ("physics", "Physics"),
    ("electricity", "Electricity"),
    ("computing", "Computing"),
]
_SUBJECT_BY_NUM = {str(i + 1): slug for i, (slug, _) in enumerate(SUBJECTS)}
_SUBJECT_BY_NAME = {slug: slug for slug, _ in SUBJECTS}
_SUBJECT_BY_NAME.update({label.lower(): slug for slug, label in SUBJECTS})

WELCOME = "Welcome to Taza-Gojo School! 📚"
MENU = (
    WELCOME
    + "\nReply with a number:\n"
    + "\n".join(f"{i+1}) {label}" for i, (_, label) in enumerate(SUBJECTS))
)
HELP = "Text START to begin a quiz, reply A/B/C/D to answer, STOP to leave."


def get_or_create_phone_user(phone):
    pu, _ = PhoneUser.objects.get_or_create(phone=phone)
    return pu


def _session(pu, channel):
    s = QuizSession.objects.filter(phone_user=pu, channel=channel).order_by("-updated_at").first()
    return s or QuizSession.objects.create(phone_user=pu, channel=channel)


def _log(pu, channel, direction, body):
    Message.objects.create(phone_user=pu, channel=channel, direction=direction, body=body[:2000])


def _letters(item):
    """Return [(letter, option_id, text)] for an MCQ item."""
    out = []
    for i, o in enumerate(item.options or []):
        if isinstance(o, dict):
            oid = o.get("id", o.get("text", str(i)))
            text = o.get("text", str(oid))
        else:
            oid, text = str(o), str(o)
        out.append((chr(65 + i), str(oid), text))
    return out


def _render_question(item, n):
    lines = [f"Q{n}: {item.prompt}"]
    for letter, _oid, text in _letters(item):
        lines.append(f"{letter}) {text}")
    return "\n".join(lines)


def _render_ussd_question(item, n):
    # USSD screens must stay short.
    opts = " ".join(f"{L}){t}" for L, _o, t in _letters(item))
    return f"Q{n}: {item.prompt[:90]}\n{opts[:90]}\nReply A/B/C/D. 0)End"


def _next_item(session):
    qs = Item.objects.filter(kind="mcq", subject=session.subject, is_active=True)
    grade = session.phone_user.grade_level
    if grade:
        qs = qs.filter(grade_min__lte=grade, grade_max__gte=grade)
    item = qs.exclude(id__in=session.asked).order_by("?").first()
    if not item:
        session.asked = []  # recycle the bank
        session.save(update_fields=["asked"])
        item = qs.exclude(id__in=session.asked).order_by("?").first()
    return item


def _ask_next(session):
    item = _next_item(session)
    session.current_item = item
    if item and item.id not in session.asked:
        session.asked = session.asked + [item.id]
    session.save(update_fields=["current_item", "asked"])
    return item


def _parse_subject(text):
    t = text.strip().lower().rstrip(".)")
    if t in _SUBJECT_BY_NUM:
        return _SUBJECT_BY_NUM[t]
    return _SUBJECT_BY_NAME.get(t)


def _parse_letter(text, letters):
    t = text.strip().upper().rstrip(".)")
    if not t:
        return None
    if t.isdigit():
        idx = int(t) - 1
        if 0 <= idx < len(letters):
            return letters[idx][1]
        return None
    if len(t) == 1 and "A" <= t <= "Z":
        idx = ord(t) - 65
        if 0 <= idx < len(letters):
            return letters[idx][1]
    return None


def _feedback(session, item, pick):
    res = grading.grade_item(item, {"value": pick})
    session.answered += 1
    if res["correct"]:
        session.score += 1
    session.save(update_fields=["answered", "score"])
    if res["correct"]:
        return f"Correct! ✅ Score {session.score}/{session.answered}."
    # Reveal the right answer.
    expected = str(item.answer.get("value", "")).lower()
    right = next((t for _L, oid, t in _letters(item) if oid.lower() == expected), None)
    return f"Not quite. The answer was {right or expected}. Score {session.score}/{session.answered}."


# --------------------------------------------------------------------------- SMS

def handle_sms(phone, text):
    """Return a list of SMS replies (each <=160 chars ideally)."""
    pu = get_or_create_phone_user(phone)
    _log(pu, Channel.SMS, "in", text)
    s = _session(pu, Channel.SMS)
    t = (text or "").strip().upper()

    if t in ("START", "JOIN", "HI", "HELLO", "MENU", "BEGIN"):
        s.state, s.subject, s.asked, s.score, s.answered = "choosing_subject", "", [], 0, 0
        s.save()
        return _out(pu, [MENU])

    if t == "STOP":
        s.state = "idle"
        s.save(update_fields=["state"])
        return _out(pu, ["You have left the quiz. Text START to play again."])

    if t == "HELP":
        return _out(pu, [HELP])

    if s.state == "choosing_subject" or not s.subject:
        subject = _parse_subject(t)
        if subject:
            s.subject, s.state, s.asked, s.score, s.answered = subject, "answering", [], 0, 0
            s.save()
            item = _ask_next(s)
            return _out(pu, [_render_question(item, 1)])
        return _out(pu, [MENU])

    if s.state == "answering" and s.current_item:
        pick = _parse_letter(t, _letters(s.current_item))
        if pick is None:
            return _out(pu, ["Please reply with A, B, C or D."])
        feedback = _feedback(s, s.current_item, pick)
        item = _ask_next(s)
        n = s.answered + 1
        return _out(pu, [feedback, _render_question(item, n)] if item else [feedback, "You have finished! Text START for more."])

    return _out(pu, [MENU])


def _out(pu, replies):
    for r in replies:
        _log(pu, Channel.SMS, "out", r)
    return replies


# -------------------------------------------------------------------------- USSD

def handle_ussd(phone, text):
    """Return (continue_session: bool, message: str) for the USSD provider."""
    pu = get_or_create_phone_user(phone)
    _log(pu, Channel.USSD, "in", text)
    s = _session(pu, Channel.USSD)
    t = (text or "").strip()

    if t == "" or s.state == "idle":
        s.state = "choosing_subject"
        s.save(update_fields=["state"])
        return True, "Taza-Gojo School\n" + "\n".join(
            f"{i+1}) {label}" for i, (_, label) in enumerate(SUBJECTS)
        )

    if s.state == "choosing_subject" or not s.subject:
        subject = _parse_subject(t)
        if not subject:
            return True, "Invalid choice. Reply 1-6."
        s.subject, s.state, s.asked, s.score, s.answered = subject, "answering", [], 0, 0
        s.save()
        item = _ask_next(s)
        return True, _render_ussd_question(item, 1)

    if s.state == "answering" and s.current_item:
        if t == "0":
            s.state = "idle"
            s.save(update_fields=["state"])
            return False, f"Thanks for learning! Score {s.score}/{s.answered}."
        pick = _parse_letter(t, _letters(s.current_item))
        if pick is None:
            return True, "Reply with A, B, C or D, or 0 to end."
        feedback = _feedback(s, s.current_item, pick)
        item = _ask_next(s)
        if not item:
            return False, f"{feedback}\nFinished! Text START again."
        return True, f"{feedback}\n{_render_ussd_question(item, s.answered + 1)}"

    return True, "Reply START to begin."
