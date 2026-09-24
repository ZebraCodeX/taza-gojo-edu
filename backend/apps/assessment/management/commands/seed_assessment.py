"""Seed a starter item bank and assessments.

Usage:  python manage.py seed_assessment
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Item, Assessment, AssessmentItem


ITEMS = [
    # --- Physics: forces and motion -------------------------------------
    dict(subject="physics", kind="mcq", grade_min=6, grade_max=9, difficulty=900,
         prompt="Which of these is a contact force?",
         options=[{"id": "a", "text": "Gravity"}, {"id": "b", "text": "Friction"},
                  {"id": "c", "text": "Magnetism"}, {"id": "d", "text": "Electrostatic"}],
         answer={"value": "b"}, hint="Contact forces need the objects to touch.",
         explanation="Friction only acts when two surfaces are in contact."),
    dict(subject="physics", kind="mcq", grade_min=6, grade_max=9, difficulty=1000,
         prompt="A car travels 150 m in 30 s. What is its average speed?",
         options=[{"id": "a", "text": "3 m/s"}, {"id": "b", "text": "5 m/s"},
                  {"id": "c", "text": "15 m/s"}, {"id": "d", "text": "4500 m/s"}],
         answer={"value": "b"}, hint="speed = distance ÷ time.",
         explanation="150 ÷ 30 = 5 m/s."),
    dict(subject="physics", kind="numeric", grade_min=6, grade_max=10, difficulty=1050,
         prompt="A force of 20 N acts on a 4 kg mass. What is the acceleration?",
         answer={"value": "5", "unit": "m/s²", "tolerance": 0.01},
         hint="Use F = m × a, so a = F ÷ m.",
         explanation="a = 20 ÷ 4 = 5 m/s²."),
    dict(subject="physics", kind="multi", grade_min=8, grade_max=11, difficulty=1250,
         prompt="Select every energy store involved when a ball is held above the ground.",
         options=[{"id": "a", "text": "Gravitational potential"}, {"id": "b", "text": "Kinetic"},
                  {"id": "c", "text": "Chemical"}, {"id": "d", "text": "Elastic"}],
         answer={"values": ["a"]}, hint="The ball is not moving yet.",
         explanation="Held still above the ground, it has gravitational potential energy."),
    dict(subject="physics", kind="math", grade_min=9, grade_max=11, difficulty=1300,
         prompt="A wave has frequency 50 Hz and wavelength 2 m. Calculate its speed (m/s).",
         answer={"value": "100", "tolerance": 0.01}, hint="v = f × λ.",
         explanation="v = 50 × 2 = 100 m/s."),
    # --- Electricity ----------------------------------------------------
    dict(subject="electricity", kind="mcq", grade_min=6, grade_max=9, difficulty=850,
         prompt="What is needed for current to flow in a circuit?",
         options=[{"id": "a", "text": "An open switch"}, {"id": "b", "text": "A complete closed loop"},
                  {"id": "c", "text": "Only a battery"}],
         answer={"value": "b"}, hint="The loop must return to the battery.",
         explanation="A closed loop lets charge flow all the way round."),
    dict(subject="electricity", kind="numeric", grade_min=8, grade_max=11, difficulty=1200,
         prompt="A current of 2 A flows through a 6 Ω resistor. What is the voltage across it?",
         answer={"value": "12", "unit": "V", "tolerance": 0.01}, hint="V = I × R.",
         explanation="V = 2 × 6 = 12 V."),
    dict(subject="electricity", kind="numeric", grade_min=8, grade_max=11, difficulty=1250,
         prompt="A 12 V supply drives a current of 3 A. What is the resistance?",
         answer={"value": "4", "unit": "Ω", "tolerance": 0.01}, hint="R = V ÷ I.",
         explanation="R = 12 ÷ 3 = 4 Ω."),
    dict(subject="electricity", kind="order", grade_min=9, grade_max=12, difficulty=1300,
         prompt="Order the steps to safely isolate a circuit before working on it.",
         options=["Notify others", "Switch off and lock off", "Test that it is dead", "Begin work"],
         answer={"values": ["Notify others", "Switch off and lock off", "Test that it is dead", "Begin work"]},
         hint="Never work until you have proved the circuit is dead.",
         explanation="Isolate, then prove dead with a tester before touching conductors."),
    dict(subject="electricity", kind="match", grade_min=9, grade_max=12, difficulty=1350,
         prompt="Match each device to its job.",
         options={"left": ["Fuse", "RCD", "Earth wire"], "right": ["Breaks on overload", "Trips on earth leakage", "Safety path for fault current"]},
         answer={"pairs": {"Fuse": "Breaks on overload", "RCD": "Trips on earth leakage", "Earth wire": "Safety path for fault current"}},
         hint="Think about what each device protects against.",
         explanation="Each protects against a different fault condition."),
    # --- Computing ------------------------------------------------------
    dict(subject="computing", kind="mcq", grade_min=6, grade_max=10, difficulty=950,
         prompt="Which construct repeats a block of code while a condition is true?",
         options=[{"id": "a", "text": "if"}, {"id": "b", "text": "while loop"},
                  {"id": "c", "text": "function"}, {"id": "d", "text": "variable"}],
         answer={"value": "b"}, hint="It keeps going round until the condition is false.",
         explanation="A while loop repeats while its condition remains true."),
    dict(subject="computing", kind="code", grade_min=7, grade_max=11, difficulty=1100,
         prompt="What is printed by:  print(2 + 3 * 4)",
         answer={"expected_output": "14"}, hint="Multiplication happens before addition.",
         explanation="3 × 4 = 12, then + 2 = 14."),
    # --- Mathematics ----------------------------------------------------
    dict(subject="math", kind="numeric", grade_min=5, grade_max=8, difficulty=850,
         prompt="Solve for x:  2x + 3 = 11",
         answer={"value": "4", "tolerance": 0.01}, hint="Subtract 3, then divide by 2.",
         explanation="2x = 8, so x = 4."),
    dict(subject="math", kind="math", grade_min=7, grade_max=10, difficulty=1150,
         prompt="Simplify:  3(x + 2) - 2x",
         answer={"value": "x+6", "tolerance": 0.01}, hint="Expand the bracket first.",
         explanation="3x + 6 - 2x = x + 6."),
    # --- English --------------------------------------------------------
    dict(subject="english", kind="short", grade_min=3, grade_max=7, difficulty=900,
         prompt="What is the past tense of the verb 'go'?",
         answer={"value": "went", "keywords": ["went"]}, hint="It is irregular.",
         explanation="Go → went."),
]

ASSESSMENTS = [
    dict(slug="physics-forces-adaptive", title="Physics: Forces & Motion (adaptive)",
         subject="physics", kind="practice", adaptive=True, max_items=5, pass_score=60,
         grade_min=6, grade_max=11, order=1,
         description="An adaptive practice set that adjusts to your level.",
         items=["PHY contact force", "PHY speed", "PHY acceleration", "PHY energy multi", "PHY wave"]),
    dict(slug="electricity-circuits-quiz", title="Electricity: Circuits & Safety",
         subject="electricity", kind="quiz", adaptive=False, max_items=6, pass_score=60,
         grade_min=7, grade_max=12, order=2,
         description="Check your understanding of circuits, Ohm's law and safety.",
         items=["ELE current flow", "ELE voltage", "ELE resistance", "ELE isolation order", "ELE device match"]),
    dict(slug="math-algebra-adaptive", title="Math: Algebra (adaptive)",
         subject="math", kind="practice", adaptive=True, max_items=5, pass_score=60,
         grade_min=5, grade_max=10, order=3,
         description="Adaptive algebra practice.",
         items=["MAT solve linear", "MAT simplify"]),
    dict(slug="computing-basics-quiz", title="Computing: Programming Basics",
         subject="computing", kind="quiz", adaptive=False, max_items=4, pass_score=60,
         grade_min=6, grade_max=11, order=4,
         description="Loops, operators and program output.",
         items=["CMP loop", "CMP output"]),
]


class Command(BaseCommand):
    help = "Create starter assessment items and assessments."

    @transaction.atomic
    def handle(self, *args, **options):
        created_items = []
        for spec in ITEMS:
            item, _ = Item.objects.update_or_create(
                prompt=spec["prompt"], subject=spec["subject"],
                defaults={k: v for k, v in spec.items() if k != "prompt"},
            )
            created_items.append(item)

        # Map short labels used in ASSESSMENTS to created items.
        label_map = {
            "PHY contact force": 0, "PHY speed": 1, "PHY acceleration": 2,
            "PHY energy multi": 3, "PHY wave": 4,
            "ELE current flow": 5, "ELE voltage": 6, "ELE resistance": 7,
            "ELE isolation order": 8, "ELE device match": 9,
            "CMP loop": 10, "CMP output": 11,
            "MAT solve linear": 12, "MAT simplify": 13,
        }

        n_assess = 0
        for spec in ASSESSMENTS:
            labels = spec.pop("items")
            assessment, _ = Assessment.objects.update_or_create(
                slug=spec["slug"], defaults=spec
            )
            n_assess += 1
            for order, label in enumerate(labels):
                idx = label_map.get(label)
                if idx is None:
                    continue
                AssessmentItem.objects.update_or_create(
                    assessment=assessment, item=created_items[idx],
                    defaults={"order": order, "points": 1.0},
                )

        self.stdout.write(self.style.SUCCESS(
            f"Assessment ready: {len(created_items)} items, {n_assess} assessments."
        ))
