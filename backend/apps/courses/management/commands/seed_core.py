"""Seed the four core courses with a starter game lesson each.

Usage:  python manage.py seed_core
"""

import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.courses.models import Course, Module, Lesson, Question

CORE = [
    {
        "slug": "english",
        "name": "English",
        "icon": "🅰️",
        "color": "#2ea44f",
        "is_core": True,
        "modules": [
            {
                "title": "Alphabet Journey",
                "lessons": [
                    {
                        "title": "Letter Catch — A to D",
                        "kind": "game",
                        "xp": 15,
                        "content": {
                            "engine": "catch",
                            "instructions": "Tap the letter that matches the sound you hear.",
                            "levels": [
                                {"targets": ["a", "b", "c", "d"], "rounds": 4},
                                {"targets": ["e", "f", "g"], "rounds": 3},
                            ],
                        },
                        "questions": [
                            {"kind": "mcq", "prompt": "Which letter comes after C?",
                             "options": ["A", "B", "D", "F"], "answer": "D",
                             "hint": "Say the alphabet out loud: A, B, C, ..."},
                        ],
                    }
                ],
            }
        ],
    },
    {
        "slug": "math",
        "name": "Math",
        "icon": "➗",
        "color": "#d29922",
        "is_core": True,
        "modules": [
            {
                "title": "Number Safari",
                "lessons": [
                    {
                        "title": "Addition Bubbles",
                        "kind": "game",
                        "xp": 15,
                        "content": {
                            "engine": "bubbles",
                            "instructions": "Pop the bubble with the correct sum.",
                            "levels": [
                                {"problems": [[2, 3], [4, 1], [5, 2], [3, 3]]},
                                {"problems": [[7, 4], [6, 6], [9, 5]], "time": 20},
                            ],
                        },
                        "questions": [
                            {"kind": "fill", "prompt": "5 + 3 = ?", "answer": "8",
                             "hint": "Count five fingers, then add three more."},
                        ],
                    }
                ],
            }
        ],
    },
    {
        "slug": "science",
        "name": "Science",
        "icon": "🔬",
        "color": "#8957e5",
        "is_core": True,
        "modules": [
            {
                "title": "Water Cycle Quest",
                "lessons": [
                    {
                        "title": "Water Cycle Explorer",
                        "kind": "game",
                        "xp": 15,
                        "content": {
                            "engine": "sequencing",
                            "instructions": "Drag the steps of the water cycle into the right order.",
                            "levels": [
                                {"steps": ["evaporation", "condensation", "precipitation", "collection"]},
                            ],
                        },
                        "questions": [
                            {"kind": "mcq", "prompt": "What turns liquid water into vapour?",
                             "options": ["Sun", "Wind", "Moon"], "answer": "Sun",
                             "hint": "Think about what heats the water."},
                        ],
                    }
                ],
            }
        ],
    },
    {
        "slug": "computing",
        "name": "Computer Programming",
        "icon": "💻",
        "color": "#1f6feb",
        "is_core": True,
        "modules": [
            {
                "title": "First Code",
                "lessons": [
                    {
                        "title": "Pixel Order: commands",
                        "kind": "game",
                        "xp": 20,
                        "content": {
                            "engine": "blockly",
                            "instructions": "Drag command blocks to help the turtle reach the flower.",
                            "levels": [
                                {"grid": 5, "blocks": ["forward", "turn_right", "forward"], "goal": "3,1"},
                            ],
                        },
                        "questions": [
                            {"kind": "code", "prompt": "What does 'turn_right' do in our puzzle?",
                             "options": ["Moves back", "Points right", "Jumping"], "answer": "Points right",
                             "hint": "Think of your own body: turning right points you which way?"},
                        ],
                    }
                ],
            }
        ],
    },
    {
        "slug": "physics",
        "name": "Physics",
        "icon": "🧲",
        "color": "#e16f24",
        "is_core": True,
        "modules": [
            {
                "title": "Forces and Motion",
                "lessons": [
                    {
                        "title": "Forces Around Us",
                        "kind": "game",
                        "xp": 20,
                        "content": {
                            "engine": "catch",
                            "instructions": "Catch the picture that shows a push or a pull.",
                            "levels": [
                                {"targets": ["push", "pull", "gravity", "friction"], "rounds": 4},
                            ],
                        },
                        "questions": [
                            {"kind": "mcq", "prompt": "Which force pulls objects towards the Earth?",
                             "options": ["Gravity", "Magnetism", "Friction"], "answer": "Gravity",
                             "hint": "It is why a dropped ball falls down."},
                            {"kind": "numeric", "prompt": "A car travels 100 m in 20 s. What is its average speed in m/s?",
                             "answer": "5", "hint": "speed = distance / time"},
                        ],
                    },
                    {
                        "title": "Energy Transfers",
                        "kind": "game",
                        "xp": 20,
                        "content": {
                            "engine": "sequencing",
                            "instructions": "Order the energy transfer in a torch, from battery to light.",
                            "levels": [
                                {"steps": ["chemical store", "electrical transfer", "light and thermal"]},
                            ],
                        },
                        "questions": [
                            {"kind": "mcq", "prompt": "Energy can be transferred but cannot be...",
                             "options": ["stored", "created or destroyed", "measured"], "answer": "created or destroyed",
                             "hint": "This is the law of conservation of energy."},
                        ],
                    },
                ],
            },
        ],
    },
    {
        "slug": "electricity",
        "name": "Electricity",
        "icon": "⚡",
        "color": "#f2cc0c",
        "is_core": True,
        "modules": [
            {
                "title": "Circuits and Safety",
                "lessons": [
                    {
                        "title": "Build a Simple Circuit",
                        "kind": "game",
                        "xp": 25,
                        "content": {
                            "engine": "blockly",
                            "instructions": "Connect the battery, switch and bulb to make the bulb light.",
                            "levels": [
                                {"components": ["battery", "switch", "bulb"], "goal": "closed circuit"},
                            ],
                        },
                        "questions": [
                            {"kind": "mcq", "prompt": "What must a circuit be for current to flow?",
                             "options": ["Open", "Closed", "Broken"], "answer": "Closed",
                             "hint": "Current needs a complete loop back to the battery."},
                            {"kind": "mcq", "prompt": "Which material is a good conductor?",
                             "options": ["Copper", "Rubber", "Plastic"], "answer": "Copper",
                             "hint": "Think about the wires inside a cable."},
                        ],
                    },
                    {
                        "title": "Ohm's Law Bubbles",
                        "kind": "game",
                        "xp": 25,
                        "content": {
                            "engine": "bubbles",
                            "instructions": "Pop the bubble with the correct value of V = I × R.",
                            "levels": [
                                {"problems": [[2, 5], [3, 4], [0.5, 10], [1.5, 4]]},
                            ],
                        },
                        "questions": [
                            {"kind": "numeric", "prompt": "A current of 2 A flows through a 6 Ω resistor. What is the voltage?",
                             "answer": "12", "hint": "V = I × R"},
                            {"kind": "numeric", "prompt": "A 12 V supply drives 3 A. What is the resistance in ohms?",
                             "answer": "4", "hint": "R = V / I"},
                        ],
                    },
                ],
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Create the four core courses with sample game lessons."

    def handle(self, *args, **options):
        created = 0
        self._seed_users()
        for c in CORE:
            course, _ = Course.objects.get_or_create(
                slug=c["slug"],
                defaults={k: v for k, v in c.items() if k != "modules"},
            )
            for m in c["modules"]:
                module, _ = Module.objects.get_or_create(
                    course=course, title=m["title"], defaults={"description": ""}
                )
                for i, l in enumerate(m["lessons"]):
                    lesson, was = Lesson.objects.get_or_create(
                        module=module,
                        title=l["title"],
                        defaults={
                            "kind": l["kind"],
                            "xp": l["xp"],
                            "content": l["content"],
                            "order": i,
                        },
                    )
                    if was:
                        created += 1
                    for q in l.get("questions", []):
                        Question.objects.get_or_create(lesson=lesson, prompt=q["prompt"], defaults=q)
        self.stdout.write(self.style.SUCCESS(f"Done. Seed data ready ({created} new lessons)."))

    def _seed_users(self):
        """Idempotent demo accounts so the app is immediately usable."""
        import os
        User = get_user_model()
        demo = [
            ("ada", "student", "Kenya", "en"),
            ("mrkwame", "teacher", "Ghana", "en"),
        ]
        for username, role, country, language in demo:
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={"role": role, "country": country, "language": language, "is_active": True},
            )
            user.set_password("test1234")
            user.save(update_fields=["password"])
        # Optional superuser for the school operator, set via env at deploy time
        # (see fly.toml secrets: DEMO_ADMIN_USERNAME / DEMO_ADMIN_PASSWORD).
        admin_name = os.environ.get("DEMO_ADMIN_USERNAME", "")
        admin_pass = os.environ.get("DEMO_ADMIN_PASSWORD", "")
        if admin_name and admin_pass:
            admin, created = User.objects.get_or_create(username=admin_name)
            admin.role = "admin"
            admin.is_staff = True
            admin.is_superuser = True
            admin.is_active = True
            admin.set_password(admin_pass)
            admin.save()
            self.stdout.write(self.style.SUCCESS(
                f"Superuser ready: {admin_name} (from env)."
            ))
        self.stdout.write(self.style.SUCCESS("Demo users ready: ada / mrkwame (password: test1234)."))

    def _clean(self):
        pass