"""Seed starter labs (coding, circuits, physics, science).

Usage:  python manage.py seed_labs
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.labs.models import Lab


LABS = [
    dict(
        slug="python-hello", title="Your first Python program",
        kind="coding", subject="computing", language="python",
        grade_min=6, grade_max=10, order=1, xp=20,
        prompt="Print the words Hello, World!",
        instructions="Write a line of Python that prints exactly: Hello, World!\n"
                     "Use print(). Capital H, capital W, comma and exclamation mark.",
        starter_code="# Type your code below\n",
        tests=[{"name": "prints Hello, World!", "expected_output": "Hello, World!"}],
        solution='print("Hello, World!")',
    ),
    dict(
        slug="python-add", title="Add two numbers",
        kind="coding", subject="computing", language="python",
        grade_min=6, grade_max=10, order=2, xp=25,
        prompt="Read two numbers and print their sum.",
        instructions="The numbers 7 and 5 are provided as variables a and b. "
                     "Print their sum.",
        starter_code="a = 7\nb = 5\n# print the sum of a and b\n",
        tests=[{"name": "sum is 12", "expected_output": "12"}],
        solution="a = 7\nb = 5\nprint(a + b)",
    ),
    dict(
        slug="js-loop", title="JavaScript: count with a loop",
        kind="coding", subject="computing", language="javascript",
        grade_min=7, grade_max=11, order=3, xp=25,
        prompt="Print the numbers 1 to 5, each on its own line.",
        instructions="Use a for loop and console.log to print 1, 2, 3, 4, 5.",
        starter_code="// Use a for loop\n",
        tests=[{"name": "prints 1..5", "expected_output": "1\n2\n3\n4\n5"}],
        solution="for (let i = 1; i <= 5; i++) console.log(i);",
    ),
    dict(
        slug="blockly-turtle", title="Blockly: move the turtle",
        kind="coding", subject="computing", language="blockly",
        grade_min=1, grade_max=5, order=4, xp=15,
        prompt="Drag blocks so the turtle reaches the flower.",
        instructions="Use 'forward' and 'turn right' blocks.",
        starter_code="",
        tests=[{"name": "turtle reaches flower", "expr": "goal", "expected": True}],
    ),
    dict(
        slug="circuit-series", title="Build a series circuit",
        kind="circuit", subject="electricity", language="none",
        grade_min=6, grade_max=11, order=5, xp=25,
        prompt="Connect a battery, a switch and a bulb so the bulb lights.",
        instructions="Click components to place them, then drag wires to make a "
                     "closed loop. Close the switch to test.",
        assets={"sim": "dc-circuit", "components": ["battery", "switch", "bulb"],
                "goal": "closed", "allow": ["battery", "bulb", "switch", "wire", "resistor"]},
        tests=[{"name": "circuit is closed and bulb lights", "expr": "bulb_lit", "expected": True}],
    ),
    dict(
        slug="circuit-ohms-law", title="Measure Ohm's law",
        kind="circuit", subject="electricity", language="none",
        grade_min=8, grade_max=12, order=6, xp=30,
        prompt="Set the supply to 6 V across a 3 Ω resistor and read the current.",
        instructions="Adjust the voltage slider and watch the ammeter. "
                     "Current should equal V / R.",
        assets={"sim": "dc-circuit", "components": ["battery", "resistor", "ammeter"],
                "goal": "current_2A", "target_current": 2.0, "resistance": 3.0},
        tests=[{"name": "current is 2 A", "expr": "current", "expected": 2.0}],
    ),
    dict(
        slug="physics-pendulum", title="Physics: pendulum swing",
        kind="physics", subject="physics", language="none",
        grade_min=5, grade_max=9, order=7, xp=20,
        prompt="Find how the length of a pendulum affects its period.",
        instructions="Change the length and time 10 swings. Record your results.",
        assets={"sim": "pendulum", "variables": ["length"], "measure": "period"},
        tests=[{"name": "longer pendulum swings slower", "expr": "period_increases_with_length", "expected": True}],
    ),
    dict(
        slug="science-water-cycle", title="Science: water cycle simulator",
        kind="science", subject="science", language="none",
        grade_min=2, grade_max=6, order=8, xp=20,
        prompt="Heat the water and watch the water cycle.",
        instructions="Move the sun slider to heat the water. Watch evaporation, "
                     "condensation and precipitation.",
        assets={"sim": "water-cycle", "variables": ["temperature"]},
        tests=[{"name": "rain forms after condensation", "expr": "rain_observed", "expected": True}],
    ),
]


class Command(BaseCommand):
    help = "Create starter labs."

    @transaction.atomic
    def handle(self, *args, **options):
        n = 0
        for spec in LABS:
            slug = spec.pop("slug")
            Lab.objects.update_or_create(slug=slug, defaults=spec)
            n += 1
        self.stdout.write(self.style.SUCCESS(f"Labs ready: {n}."))
