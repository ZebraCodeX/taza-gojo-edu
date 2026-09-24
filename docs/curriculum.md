# Curriculum

Taza-Gojo is **Ethiopia-first** but **Cambridge/IGCSE-aligned**, and must stay
flexible enough to serve any African country without forking the content.

## Model

```
Framework (Cambridge IGCSE / Ethiopia MoE / Ethiopia TVET / …)
  └─ Strand (subject + topic area, e.g. "Electricity and Magnetism")
       └─ Outcome (one assessable can-do statement + grade band + Elo difficulty)
```

`OutcomeLink` connects any content object (lesson, assessment, lab) to the
outcomes it teaches or assesses, using a generic `target_model`/`target_id` pair
so this app never imports the content apps:

```python
OutcomeLink.objects.create(outcome=phy, target_model="courses.Lesson", target_id=12, relation="teaches")
```

`Mapping` records cross-framework equivalence (Cambridge ↔ Ethiopian ↔ TVET) with
a relation (`equivalent`/`partial`/`broader`/`narrower`) and confidence, so one
authored lesson can satisfy several countries' outcomes.

## Honesty about official codes

Outcome statements are written as original can-do statements aligned to each
framework's published topic structure. They are **not** verbatim copies of
copyrighted syllabi. `Outcome.reference` is intentionally blank unless an
official code has been verified; internal codes (`PHY-6.1`, `ELE-T7`) are stable
platform-owned identifiers. Swap in official codes later without touching links.

## Seeded frameworks

| Slug | Authority | Covers |
|---|---|---|
| `cambridge-primary` | Cambridge International | Stages 1-6 |
| `cambridge-lower-secondary` | Cambridge International | Stages 7-9 |
| `cambridge-igcse` | Cambridge International | Ages 14-16 |
| `ethiopia-moe` | Ministry of Education | Primary 1-6 / middle 7-8 / secondary 9-12 |
| `ethiopia-tvet` | TVET Agency | Electrical installation & solar PV |

Seed with:

```bash
python manage.py seed_curriculum
```

## API

- `GET /api/v1/curriculum/frameworks/` — full tree (frameworks → strands → outcomes)
- `GET /api/v1/curriculum/frameworks/<slug>/outcomes/?subject=physics&grade=9`
- `GET /api/v1/curriculum/outcomes/?subject=electricity&grade=10`
- `GET /api/v1/curriculum/mappings/?outcome=ELE-6.4`

## Adding a country

1. Add a `Framework` (+ `Strand`/`Outcome` rows) via the seed or Django admin.
2. Add `Mapping` rows to the closest Cambridge/Ethiopian outcomes.
3. Reuse existing lessons/assessments/labs by adding `OutcomeLink`s.
