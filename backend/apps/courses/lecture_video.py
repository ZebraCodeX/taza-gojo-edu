"""Build a HyperFrames composition (HTML -> video) from a Lesson.

Each lesson becomes a short, scripted "video lecture": a title card, the
"how to play" instructions, an explainer slide derived from the game script,
one quiz slide (with the answer revealed), and an outro. The composition is a
self-contained HTML file that the `hyperframes` CLI renders to MP4.
"""

import html as htmlmod

GSAP_CDN = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"

W, H = 1920, 1080


def _esc(value):
    return htmlmod.escape(str(value or ""), quote=True)


def build_lecture_html(lesson, module_title, course):
    """Return (html, total_seconds) for the lesson's video lecture."""
    content = lesson.content or {}
    engine = content.get("engine", "")
    instructions = content.get("instructions", "")

    slides = []  # (start, duration, title, body_html, accent)

    t = 0.0

    def add(duration, html_fragment):
        nonlocal t
        slides.append((t, duration, html_fragment))
        t += duration

    accent = course.color or "#3b5bdb"

    # 1 — title card
    add(5.0, f"""
      <div class="in kicker">{_esc(course.icon)} {_esc(course.name)} · {_esc(module_title)}</div>
      <h1 class="in">{_esc(lesson.title)}</h1>
      <p class="in sub">Video lecture · {lesson.duration_minutes} min · +{lesson.xp} XP</p>
    """)

    # 2 — how it works
    if instructions:
        add(6.0, f"""
          <div class="in kicker">How it works</div>
          <h2 class="in">Your goal in this lesson</h2>
          <p class="in body">{_esc(instructions)}</p>
        """)

    # 3 — the learning content, engine-aware
    add(11.0, _engine_slides(engine, content))

    # 4 — quiz (answers revealed)
    for q in lesson.questions.all()[:2]:
        options = " · ".join(str(o) for o in (q.options or [])) or ""
        opts_line = f'<p class="in body dimbig">{_esc(options)}</p>' if options else ""
        add(8.0, f"""
          <div class="in kicker">Check yourself</div>
          <h2 class="in">Quiz</h2>
          <p class="in body q">{_esc(q.prompt)}</p>
          {opts_line}
          <p class="in answer">Answer: <b>{_esc(q.answer)}</b></p>
        """)

    # 5 — outro
    add(4.0, """
      <div class="in kicker">Almost there</div>
      <h2 class="in">Now play it in the app</h2>
      <p class="in body">Earn XP and stars, and save your progress —
         it syncs even on the slowest connection.</p>
    """)

    total = t
    return render_composition(slides, accent, total), total


def _engine_slides(engine, content):
    """Return the body HTML for the 'learn it' slide, derived from the script."""
    if engine == "catch":
        targets = []
        rounds = 0
        for lv in content.get("levels", []):
            for tgt in lv.get("targets", []):
                if tgt not in targets:
                    targets.append(tgt)
            rounds += lv.get("rounds", 0)
        chips = "".join(f'<span class="in chip">{_esc(c)}</span>' for c in targets)
        return f"""
          <div class="in kicker">Letters in this lesson</div>
          <h2 class="in">Meet the letters</h2>
          <div class="in chips">{chips}</div>
          <p class="in body">Tap the letter that matches the sound you hear —
             {rounds} quick rounds across {max(1, len(content.get('levels', [])))} levels.</p>
        """
    if engine == "bubbles":
        rows = []
        seen = set()
        for lv in content.get("levels", []):
            for a, b in lv.get("problems", []):
                key = (a, b)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(f"<li class=\"in\"><b>{a} + {b}</b> = {a + b}</li>")
            if len(rows) >= 8:
                break
        lis = "".join(rows) or "<li class=\"in\">Simple additions to warm up your brain.</li>"
        return f"""
          <div class="in kicker">Addition</div>
          <h2 class="in">Pop the correct sum</h2>
          <ul class="learn">{lis}</ul>
          <p class="in body">Remember: {rows[0].split('=')[0].strip() if rows else 'add left to right'} —
             the plus tells you to put them together.</p>
        """
    if engine == "sequencing":
        steps = content.get("levels", [{}])[0].get("steps", []) if content.get("levels") else []
        lis = "".join(f"<li class=\"in\">{_esc(s)}</li>" for s in steps)
        return f"""
          <div class="in kicker">Order matters</div>
          <h2 class="in">The steps, in order</h2>
          <ol class="learn">{lis}</ol>
          <p class="in body">A sequence is a set of steps you follow one after another.</p>
        """
    if engine == "blockly":
        lv = (content.get("levels") or [{}])[0]
        goal = lv.get("goal", "?")
        grid = lv.get("grid", 4)
        return f"""
          <div class="in kicker">Commands</div>
          <h2 class="in">Guide your robot to {_esc(goal)}</h2>
          <p class="in body">Build a short list of commands
             (<b>forward</b>, <b>turn right</b>) on a {grid}×{grid} grid
             so the robot reaches the goal tile.</p>
        """
    return """
      <div class="in kicker">Explore</div>
      <h2 class="in">What you'll learn here</h2>
      <p class="in body">This lesson introduces a new idea. Watch, play, and
         the steps will stick.</p>
    """


def render_composition(slides, accent, total):
    """Assemble the standalone HyperFrames HTML document."""
    sections = []
    timeline = []
    for idx, (start, duration, body) in enumerate(slides):
        sections.append(f"""
        <section id="s{idx}" class="clip" data-start="{start:.2f}" data-duration="{duration:.2f}" data-track-index="1">
          <div class="slide">{body}</div>
        </section>""")
        timeline.append(
            f'tl.fromTo("#s{idx} .in", {{opacity:0, y:46}}, {{opacity:1, y:0, duration:0.55, stagger:0.22, ease:"power2.out"}}, {start + 0.45:.2f});'
        )
    sections_html = "\n".join(sections)
    tl = "\n".join(timeline)

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="{GSAP_CDN}"></script>
    <style>
      * {{ box-sizing: border-box; }}
      html, body {{ margin: 0; padding: 0; font-family: 'Segoe UI', 'Helvetica Neue', Arial, system-ui, sans-serif; -webkit-font-smoothing: antialiased; }}
      #root {{
        position: relative;
        width: {W}px;
        height: {H}px;
        overflow: hidden;
        background: linear-gradient(140deg, #241a63 0%, {accent} 70%, #7c3aed 100%);
        color: #fff;
      }}
      .clip {{ position: absolute; inset: 0; display: grid; place-items: center; padding: 90px; }}
      .slide {{ width: 100%; height: 100%; display: flex; flex-direction: column; justify-content: center; text-align: left; }}
      h1 {{ font-size: 118px; font-weight: 900; margin: 10px 0; letter-spacing: -1px; }}
      h2 {{ font-size: 92px; font-weight: 800; margin: 6px 0 14px; }}
      .kicker {{ font-size: 44px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; opacity: 0.82; }}
      .sub {{ font-size: 40px; opacity: 0.9; }}
      .body {{ font-size: 52px; line-height: 1.45; max-width: 1560px; opacity: 0.95; }}
      .q {{ font-size: 66px; font-weight: 700; }}
      .answer {{ font-size: 54px; margin-top: 26px; background: rgba(255,255,255,0.14); padding: 18px 30px; border-radius: 22px; width: fit-content; }}
      .answer b {{ color: {accent}; background:#fff; padding: 4px 16px; border-radius: 14px; }}
      .dimbig {{ opacity: 0.85; }}
      .learn {{ list-style: none; padding: 0; margin: 16px 0; font-size: 56px; line-height: 1.5; }}
      .learn li {{ margin: 10px 0; }}
      .learn b {{ font-size: 64px; }}
      .chips {{ display: flex; gap: 22px; flex-wrap: wrap; margin: 26px 0; }}
      .chip {{ font-size: 90px; font-weight: 900; width: 160px; height: 160px; border-radius: 999px;
                 display: grid; place-items: center; background: #fff; color: {accent}; box-shadow: 0 10px 30px rgba(0,0,0,0.25); text-transform: uppercase; }}
      .in {{ opacity: 0; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total:.2f}" data-width="{W}" data-height="{H}">
{sections_html}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
{tl}
      window.__timelines.main = tl;
    </script>
  </body>
</html>
"""


def duration_for_probe(mp4_path, fallback):
    """Seconds for a rendered MP4 using ffprobe when available."""
    import shutil
    import subprocess

    if shutil.which("ffprobe"):
        try:
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", str(mp4_path)],
                capture_output=True, text=True, timeout=30,
            )
            if out.returncode == 0 and out.stdout.strip():
                return int(float(out.stdout.strip()))
        except Exception:
            pass
    return fallback