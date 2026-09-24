"""Seed curriculum frameworks and outcomes.

Usage:  python manage.py seed_curriculum

Content policy
--------------
Statements below are written as plain "can-do" outcomes aligned to the named
framework's published topic structure. They are *not* verbatim reproductions of
copyrighted syllabus documents, and ``reference`` is left blank unless an
official code has been verified. Internal codes (e.g. ``PHY-6.1``) are stable
identifiers the platform owns; swap in official codes later without touching
content links.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.curriculum.models import Framework, Strand, Outcome, Mapping


# ---------------------------------------------------------------------------
# Reusable outcome sets
# ---------------------------------------------------------------------------

PHYSICS_PRIMARY = [
    ("PHY-P1", "Explore pushes and pulls and describe how forces change motion.", 1, 3, 800),
    ("PHY-P2", "Investigate light and shadows and describe how sound travels.", 2, 4, 850),
    ("PHY-P3", "Use simple machines (ramps, levers) to move loads and explain the trade-off.", 3, 5, 900),
    ("PHY-P4", "Build a simple series circuit with a battery, bulb and switch.", 4, 6, 950),
    ("PHY-P5", "Classify materials as conductors or insulators and explain electrical safety.", 4, 6, 1000),
]

PHYSICS_LOWER = [
    ("PHY-L1", "Measure length, mass, time and volume using appropriate instruments and units.", 7, 8, 1000),
    ("PHY-L2", "Describe motion using speed, distance and time; interpret distance-time graphs.", 7, 9, 1050),
    ("PHY-L3", "Explain energy stores and transfers, including conservation of energy.", 7, 9, 1080),
    ("PHY-L4", "Describe density and use it to explain floating and sinking.", 7, 8, 1020),
    ("PHY-L5", "Investigate pressure in solids, liquids and gases.", 8, 9, 1100),
    ("PHY-L6", "Describe the magnetic effect of a current and build an electromagnet.", 8, 9, 1150),
]

PHYSICS_IGCSE = [
    ("PHY-6.1", "Use and rearrange the equations for speed, acceleration and force (v=u+at, F=ma).", 9, 11, 1250),
    ("PHY-6.2", "Apply Newton's laws to explain motion, including terminal velocity and momentum.", 9, 11, 1300),
    ("PHY-6.3", "Calculate work, power and efficiency and apply conservation of energy.", 9, 11, 1280),
    ("PHY-6.4", "Describe wave properties (amplitude, wavelength, frequency) and use v=fλ.", 9, 11, 1270),
    ("PHY-6.5", "Explain reflection, refraction and the behaviour of light through lenses.", 9, 11, 1290),
    ("PHY-6.6", "Describe the particle model and relate it to temperature, pressure and changes of state.", 9, 10, 1200),
    ("PHY-6.7", "Describe thermal energy transfer by conduction, convection and radiation.", 9, 10, 1210),
    ("PHY-6.8", "Apply the principle of moments and explain stability.", 9, 11, 1260),
]

ELECTRICITY_IGCSE = [
    ("ELE-6.1", "Draw and interpret circuit diagrams using standard symbols.", 9, 11, 1200),
    ("ELE-6.2", "Calculate current, charge and time using Q=It.", 9, 11, 1220),
    ("ELE-6.3", "Apply Ohm's law and calculate resistance from V-I graphs.", 9, 11, 1260),
    ("ELE-6.4", "Analyse series and parallel circuits: current, voltage and equivalent resistance.", 9, 11, 1320),
    ("ELE-6.5", "Calculate electrical power and energy (P=VI, E=Pt) and the cost of electricity.", 9, 11, 1300),
    ("ELE-6.6", "Explain the magnetic effect of current and the operation of motors and relays.", 9, 11, 1350),
    ("ELE-6.7", "Describe electromagnetic induction and how generators produce electricity.", 10, 11, 1400),
    ("ELE-6.8", "Compare AC and DC and describe the role of fuses, earthing and circuit breakers.", 9, 11, 1280),
]

ELECTRICITY_TVET = [
    ("ELE-T1", "Interpret electrical drawings, symbols and wiring schedules to plan an installation.", 9, 12, 1200),
    ("ELE-T2", "Select and safely use hand tools, testers and a digital multimeter.", 9, 12, 1150),
    ("ELE-T3", "Install and terminate cables and accessories to a domestic lighting circuit.", 9, 12, 1300),
    ("ELE-T4", "Test a circuit for continuity, insulation resistance and earth continuity.", 9, 12, 1350),
    ("ELE-T5", "Apply earthing, bonding and RCD protection to meet safety requirements.", 9, 12, 1400),
    ("ELE-T6", "Diagnose and repair common faults in domestic electrical circuits.", 9, 12, 1450),
    ("ELE-T7", "Design and size a small off-grid solar PV system (panel, charge controller, battery, inverter).", 9, 12, 1500),
    ("ELE-T8", "Install, test and maintain a solar home system safely.", 9, 12, 1520),
    ("ELE-T9", "Apply electrical safety regulations and safe isolation procedures.", 9, 12, 1250),
]

COMPUTING_PRIMARY = [
    ("CMP-P1", "Give and follow precise sequences of instructions (algorithms) to solve a task.", 1, 4, 850),
    ("CMP-P2", "Predict the output of a short sequence of commands and debug simple errors.", 3, 6, 950),
    ("CMP-P3", "Use loops to repeat actions and explain why repetition saves work.", 4, 6, 1000),
]

COMPUTING_IGCSE = [
    ("CMP-6.1", "Design algorithms using sequence, selection and iteration and represent them as pseudocode/flowcharts.", 8, 11, 1250),
    ("CMP-6.2", "Write, test and debug programs that use variables, input/output and arithmetic.", 8, 11, 1280),
    ("CMP-6.3", "Use conditional statements and loops to solve problems.", 8, 11, 1320),
    ("CMP-6.4", "Use functions/procedures to structure a program and avoid repetition.", 9, 11, 1380),
    ("CMP-6.5", "Use lists/arrays and basic string operations to process data.", 9, 11, 1420),
    ("CMP-6.6", "Explain binary representation of data and convert between denary and binary.", 9, 11, 1300),
    ("CMP-6.7", "Describe the fetch-decode-execute cycle and the role of main memory.", 9, 11, 1350),
]

ENGLISH_PRIMARY = [
    ("ENG-P1", "Recognise and write the letters of the alphabet and their common sounds.", 1, 2, 700),
    ("ENG-P2", "Blend sounds to read simple three-letter words.", 1, 3, 750),
    ("ENG-P3", "Read short sentences aloud with understanding.", 2, 4, 850),
    ("ENG-P4", "Write a short paragraph with capital letters and full stops.", 3, 6, 950),
    ("ENG-P5", "Retell a story in the correct order and answer questions about it.", 3, 6, 1000),
]

MATH_PRIMARY = [
    ("MAT-P1", "Count, read and write numbers to 100 and compare them.", 1, 2, 700),
    ("MAT-P2", "Add and subtract numbers within 20 using objects and mentally.", 1, 3, 780),
    ("MAT-P3", "Understand place value in two- and three-digit numbers.", 2, 4, 850),
    ("MAT-P4", "Recall multiplication facts and multiply two-digit by one-digit numbers.", 3, 5, 950),
    ("MAT-P5", "Recognise and compare simple fractions and measure length and mass.", 3, 6, 1000),
]

MATH_LOWER = [
    ("MAT-L1", "Use positive and negative integers and order them on a number line.", 7, 8, 1050),
    ("MAT-L2", "Solve linear equations in one variable.", 7, 9, 1150),
    ("MAT-L3", "Use ratio, proportion and percentages to solve real problems.", 7, 9, 1120),
    ("MAT-L4", "Calculate area and perimeter of triangles, quadrilaterals and circles.", 7, 9, 1180),
    ("MAT-L5", "Interpret and construct statistical charts and calculate averages.", 7, 9, 1100),
]

MATH_IGCSE = [
    ("MAT-6.1", "Solve simultaneous linear equations algebraically.", 9, 11, 1300),
    ("MAT-6.2", "Expand and factorise algebraic expressions and rearrange formulae.", 9, 11, 1320),
    ("MAT-6.3", "Apply Pythagoras' theorem and trigonometry to right-angled triangles.", 9, 11, 1350),
    ("MAT-6.4", "Solve quadratic equations by factorising and using the formula.", 10, 11, 1400),
    ("MAT-6.5", "Use probability to calculate combined event likelihoods.", 9, 11, 1280),
    ("MAT-6.6", "Apply the circle theorems to find unknown angles.", 10, 11, 1420),
]

SCIENCE_PRIMARY = [
    ("SCI-P1", "Identify the basic needs of plants and animals and label plant parts.", 1, 3, 780),
    ("SCI-P2", "Describe the water cycle and changes of state in everyday life.", 2, 4, 850),
    ("SCI-P3", "Group living things by observable features.", 3, 5, 900),
    ("SCI-P4", "Describe the main body systems (digestion, circulation, breathing).", 4, 6, 1000),
]

SCIENCE_LOWER = [
    ("SCI-L1", "Use a microscope and describe cells as the building blocks of life.", 7, 8, 1050),
    ("SCI-L2", "Describe photosynthesis and respiration and their importance.", 7, 9, 1120),
    ("SCI-L3", "Explain the particle model of matter and separation techniques.", 7, 9, 1100),
    ("SCI-L4", "Describe the structure of the Earth and the rock cycle.", 8, 9, 1150),
]


def _subject_strands(subject, entries):
    """Group a flat list of (code, statement, gmin, gmax, diff) into one strand."""
    return [{
        "subject": subject,
        "code": "",
        "title": {
            "physics": "Physics",
            "electricity": "Electricity",
            "computing": "Computing",
            "english": "English",
            "math": "Mathematics",
            "science": "Science",
        }.get(subject, subject.title()),
        "outcomes": entries,
    }]


FRAMEWORKS = [
    {
        "slug": "cambridge-primary",
        "name": "Cambridge Primary",
        "country": "",
        "authority": "Cambridge International",
        "version": "2024",
        "order": 1,
        "description": "International primary programme, stages 1-6 (ages 5-11).",
        "strands": (
            _subject_strands("english", ENGLISH_PRIMARY)
            + _subject_strands("math", MATH_PRIMARY)
            + _subject_strands("science", SCIENCE_PRIMARY)
            + _subject_strands("physics", PHYSICS_PRIMARY)
            + _subject_strands("computing", COMPUTING_PRIMARY)
        ),
    },
    {
        "slug": "cambridge-lower-secondary",
        "name": "Cambridge Lower Secondary",
        "country": "",
        "authority": "Cambridge International",
        "version": "2024",
        "order": 2,
        "description": "International lower secondary programme, stages 7-9 (ages 11-14).",
        "strands": (
            _subject_strands("math", MATH_LOWER)
            + _subject_strands("science", SCIENCE_LOWER)
            + _subject_strands("physics", PHYSICS_LOWER)
        ),
    },
    {
        "slug": "cambridge-igcse",
        "name": "Cambridge IGCSE",
        "country": "",
        "authority": "Cambridge International",
        "version": "2024",
        "order": 3,
        "description": "International upper secondary, typically ages 14-16.",
        "strands": (
            _subject_strands("math", MATH_IGCSE)
            + _subject_strands("physics", PHYSICS_IGCSE)
            + _subject_strands("electricity", ELECTRICITY_IGCSE)
            + _subject_strands("computing", COMPUTING_IGCSE)
        ),
    },
    {
        "slug": "ethiopia-moe",
        "name": "Ethiopia MoE General Education",
        "country": "Ethiopia",
        "authority": "Ministry of Education",
        "version": "2023",
        "order": 10,
        "description": "Ethiopian general education curriculum (primary 1-6, middle 7-8, secondary 9-12).",
        "strands": (
            _subject_strands("english", ENGLISH_PRIMARY)
            + _subject_strands("math", MATH_PRIMARY)
            + _subject_strands("science", SCIENCE_PRIMARY)
            + _subject_strands("physics", PHYSICS_PRIMARY)
            + _subject_strands("computing", COMPUTING_PRIMARY)
        ),
    },
    {
        "slug": "ethiopia-tvet",
        "name": "Ethiopia TVET",
        "country": "Ethiopia",
        "authority": "TVET Agency",
        "version": "2023",
        "order": 11,
        "description": "Technical and Vocational Education and Training occupational standards.",
        "strands": _subject_strands("electricity", ELECTRICITY_TVET),
    },
]

# Cross-framework equivalence: Cambridge IGCSE electricity <-> TVET electrical
MAPPINGS = [
    ("ELE-6.1", "ELE-T1", "equivalent", 0.7, "Circuit symbols/reading drawings"),
    ("ELE-6.3", "ELE-T2", "partial", 0.6, "Ohm's law underpins testing with a multimeter"),
    ("ELE-6.4", "ELE-T3", "partial", 0.6, "Series/parallel theory applied to installation"),
    ("ELE-6.6", "ELE-T6", "partial", 0.5, "Motor/fault-finding overlap"),
    ("ELE-6.8", "ELE-T5", "partial", 0.6, "Protection and safety"),
    ("ELE-6.5", "ELE-T7", "partial", 0.5, "Power calculations in PV sizing"),
]


class Command(BaseCommand):
    help = "Create curriculum frameworks, strands, outcomes and cross-mappings."

    @transaction.atomic
    def handle(self, *args, **options):
        outcomes_by_code = {}
        n_fw = n_out = 0

        for raw in FRAMEWORKS:
            fw = dict(raw)
            strands = fw.pop("strands")
            framework, _ = Framework.objects.update_or_create(
                slug=fw["slug"], defaults=fw
            )
            n_fw += 1
            for si, st in enumerate(strands):
                strand, _ = Strand.objects.update_or_create(
                    framework=framework,
                    subject=st["subject"],
                    code=st.get("code", ""),
                    title=st["title"],
                    defaults={"order": si, "description": st.get("description", "")},
                )
                for oi, (code, statement, gmin, gmax, diff) in enumerate(st["outcomes"]):
                    outcome, _ = Outcome.objects.update_or_create(
                        strand=strand, code=code,
                        defaults={
                            "statement": statement,
                            "grade_min": gmin,
                            "grade_max": gmax,
                            "difficulty": float(diff),
                            "order": oi,
                        },
                    )
                    outcomes_by_code.setdefault(code, outcome)
                    n_out += 1

        n_map = 0
        for from_code, to_code, rel, conf, note in MAPPINGS:
            a = outcomes_by_code.get(from_code)
            b = outcomes_by_code.get(to_code)
            if a and b:
                Mapping.objects.update_or_create(
                    from_outcome=a, to_outcome=b,
                    defaults={"relation": rel, "confidence": conf, "note": note},
                )
                n_map += 1

        self.stdout.write(self.style.SUCCESS(
            f"Curriculum ready: {n_fw} frameworks, {n_out} outcomes, {n_map} mappings."
        ))
