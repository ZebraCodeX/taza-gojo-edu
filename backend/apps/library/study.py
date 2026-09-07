"""apps.library.study — turn any catalog entry into an offline-readable study guide.

The catalog mixes `content`-based study packs with `url`-based links to free
online sources. To make EVERY material downloadable for offline study, we render
a compact HTML guide for link-only entries at seed time: what the resource is,
a topical outline, how to study it, and practice ideas. Guides are small (a few
KB) and keep the SW/IndexedDB download tiny on 2G.
"""

import re
import html as _html

# Subject-specific topic banks, chosen so every entry gets a useful outline even
# when the catalog has no explicit `outline` for it yet.
TOPIC_BANK = {
    "math": [
        "Numbers and place value — read, write and compare numbers",
        "Fractions, decimals and percentages and how they connect",
        "Operations: addition, subtraction, multiplication and division",
        "Algebra basics — variables, expressions and solving for unknowns",
        "Geometry — shapes, angles, area and perimeter",
        "Data and probability — charts, averages and chance",
    ],
    "english": [
        "Reading comprehension — finding the main idea and details",
        "Vocabulary building — new words in context",
        "Grammar and sentence structure",
        "Writing clearly — paragraphs, essays and summaries",
        "Listening and speaking practice",
        "Grammar of storytelling — plot, characters and setting",
    ],
    "science": [
        "The scientific method — observe, question, test, conclude",
        "Life science — cells, plants, animals and ecosystems",
        "Physical science — forces, energy, matter and motion",
        "Earth and space — weather, water cycles and the solar system",
        "Working safely with practical experiments",
        "Reading and making sense of charts and models",
    ],
    "computing": [
        "What a computer program is and how to read code",
        "Variables, data and simple types",
        "Logic: conditionals, loops and functions",
        "Building small projects step by step",
        "Debugging — finding and fixing mistakes",
        "Hands-on practice: type the examples and change them",
    ],
    "general": [
        "Understand the big idea of each unit first",
        "Practice a little every day — short and regular beats long and rare",
        "Explain what you learned to a friend or family member",
        "Review mistakes and turn them into sharp notes",
        "Connect new ideas to things you already know",
    ],
}

PRACTICE = {
    "book": ["Read one chapter, then close the book and retell it in your own words.",
             "Copy 3 key sentences and rewrite each one differently.",
             "Make a one-page summary diagram after every chapter.",
             "Pick 5 new words from each chapter and use them in sentences."],
    "article": ["Read it twice: once for the big picture, once for details.",
                "Write one question you still have after reading.",
                "Summarise the main point in under 40 words."],
    "worksheet": ["Do 3 problems with the worked example covered, then check.",
                  "Time yourself — aim to get faster without losing accuracy.",
                  "Turn a wrong answer into a 'what I learned' note."],
    "course": ["Follow the course in the order given — each lesson builds on the last.",
               "Pause after each lesson and do the check yourself.",
               "Keep a notebook of commands/formulas you meet."],
    "video": ["Watch in short bursts and pause to repeat key moments.",
              "Take notes on each video — you'll remember twice as much.",
              "Re-watch the hardest part once more before moving on."],
    "study_pack": ["Work through the pack from start to finish.",
                   "Do all the mini-exercises before reading the answers.",
                   "Re-read your weak spots one more time the next day."],
}


def _fmt(x):
    return " ".join(str(x).split())


def _titles(topic, title, outline):
    if outline:
        return [_fmt(t) for t in outline]
    words = re.findall(r"\b[A-Za-z]{5,}\b", _fmt(title).lower())
    bank = TOPIC_BANK.get(topic, TOPIC_BANK["general"])
    used = set()
    picks = []
    for w in words:
        for b in bank:
            if w in b.lower() and b not in used:
                picks.append(b)
                used.add(b)
        if len(picks) >= 4:
            break
    return (picks + [b for b in bank if b not in used])[:6]


def outline_for(material) -> list:
    """Topical item list for a Material (used by the study guide + admin UI)."""
    return _titles(material.subject or "general", material.title, material.outline)


def build_study_html(material) -> str:
    """Deterministic, screen-reader-friendly HTML guide for any Material."""
    topic = material.subject or "general"
    kind = material.kind or "book"
    outline = _titles(topic, material.title, material.outline)
    grade = grade_name(material.grade_start, material.grade_end)

    def li(items):
        return "".join(f"<li>{_html.escape(_fmt(i))}</li>" for i in items)

    sections = [
        "<h2>What this is</h2>",
        f"<p>{_html.escape(_fmt(material.description or material.title))}</p>",
        f"<p><b>Level:</b> {grade} &nbsp;·&nbsp; <b>Kind:</b> {kind.replace('_', ' ')}"
        + (f" &nbsp;·&nbsp; <b>Source:</b> {_html.escape(_fmt(material.provider))}" if material.provider else "")
        + (f" &nbsp;·&nbsp; {_html.escape(_fmt(material.license_note))}" if material.license_note else "")
        + "</p>",
        "<h2>What you will learn</h2>",
        f"<ul>{li(outline)}</ul>",
        "<h2>How to study this offline</h2>",
        f"<ul>{li(PRACTICE.get(kind, PRACTICE['article']))}</ul>",
        "<h2>Keep going</h2>",
        "<p>Open the original source whenever you have data to go deeper, and "
        "ask the AI tutor about anything here — it is loaded with this subject "
        "too.</p>",
    ]
    if material.url:
        sections.append(
            f"<p><a href=\"{_html.escape(material.url)}\" rel=\"noopener\">Open the original source ↗</a></p>"
        )
    return "\n".join(sections)


def grade_name(start, end):
    def fmt(g):
        return "College" if g >= 13 else f"Grade {g}"
    if start >= 13:
        return "College"
    if end >= 13 and start <= 12:
        return f"Grade {start} + college"
    if start == end:
        return fmt(start)
    return f"Grades {start}–{end}"