# Assessment

Reusable item bank + adaptive delivery + server-side auto-grading + verifiable
certificates. Built to work on a 2G phone: items are tiny JSON, and the whole
attempt flow is a handful of small requests.

## Item kinds

| kind | auto-graded | notes |
|---|---|---|
| `mcq` | ✅ | single correct option |
| `multi` | ✅ partial | Jaccard partial credit |
| `numeric` | ✅ | tolerance + **unit** check (right number, wrong unit = half) |
| `math` | ✅ | numeric equivalence via safe expression evaluation |
| `code` | ✅ | compares program output |
| `order` | ✅ partial | positional partial credit |
| `match` | ✅ partial | pairs |
| `short` | ✅ | exact or required-keyword match |
| `essay` | ❌ | flagged `needs_manual` for teacher review |

Answers are **never** sent to students: `ItemStudentSerializer` strips
`answer`/`solution`. Grading happens in `grading.py`; math is evaluated with an
AST-whitelisted evaluator (no `eval`, no imports).

## Adaptive engine

`adaptive.py` uses a simple Elo model:

```
expected = 1 / (1 + 10^((difficulty - theta) / 400))
theta   += K * (score - expected)        # K = 24
```

The next item is the unanswered bank item closest to the learner's current
`theta`, keeping success near the 50-70% learning sweet spot. Fixed-form
assessments serve authored order instead. Upgrade path: 2PL IRT once response
volume allows calibration.

## Flow

```
POST /api/v1/assessment/assessments/<slug>/start/     -> attempt + first item
POST /api/v1/assessment/attempts/<id>/answer/          -> grade + next item
POST /api/v1/assessment/attempts/<id>/submit/          -> final score (+ certificate)
GET  /api/v1/assessment/attempts/<id>/                 -> full attempt + responses
GET  /api/v1/assessment/certificates/                  -> my certificates
GET  /api/v1/assessment/certificates/verify/<code>/    -> public verification
```

## Certificates

Issued on pass (one per user+assessment). Each has a random code (`TG-…`) and a
`verify_hash = sha256(code:score:SECRET_KEY)`; the public verify endpoint returns
`{valid, title, score, issued_at}` so anyone can confirm authenticity. The
frontend certificate page is printable to PDF.

## Seed

```bash
python manage.py seed_assessment   # 15 items, 4 assessments (physics/electricity/math/computing)
```
