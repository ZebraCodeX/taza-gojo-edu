# Feature-phone gateway (SMS / USSD / voice)

Reaches learners with **no smartphone**. They take the same quizzes as the app
over plain SMS or USSD, using the shared `assessment.Item` bank and grader.

## Flow

SMS:

```
Learner: START
School : Welcome to Taza-Gojo School! 📚 Reply with a number: 1) Math …
Learner: 1
School : Q1: What is 2 + 2?  A) 3  B) 4  C) 5   (Reply A, B, C or D.)
Learner: B
School : Correct! ✅ Score 1/1.
         Q2: … (next question)
```

USSD is a stateful menu (`CON`/`END` screens, max ~180 chars each):

```
*   -> CON 1)Math 2)English …
1   -> CON Q1: … A)… B)… (reply A/B/C/D, 0)End)
B   -> CON Correct! … Q2: …
0   -> END Thanks for learning! Score 1/2.
```

## Providers

`SMS_PROVIDER=console` (default) logs messages instead of sending, so the whole
flow is testable offline. Set `SMS_PROVIDER=africastalking` plus:

```
AFRICASTALKING_USERNAME=
AFRICASTALKING_API_KEY=
AFRICASTALKING_SENDER=   # optional short code
```

USSD replies are returned synchronously in the provider's expected
`CON …` / `END …` plain-text format.

## Webhooks

| Endpoint | Provider payload |
|---|---|
| `POST /api/v1/gateway/sms/` | `from`, `text` (form or JSON) |
| `POST /api/v1/gateway/ussd/` | `phoneNumber`, `text` |

Set `GATEWAY_WEBHOOK_TOKEN` and pass it as `?token=` or the `X-Gateway-Token`
header to authenticate the aggregator. Leave it empty only for local dev.

## Try it without a phone

```bash
python manage.py gateway_sim +251900000001 START
python manage.py gateway_sim +251900000001 1
python manage.py gateway_sim +251900000001 B
python manage.py gateway_sim --ussd +251900000001 1
```

## Data

- `PhoneUser` — phone → optional app account, language, grade.
- `QuizSession` — per-phone state, subject, current item, score.
- `Message` — audit of every inbound/outbound message.

## Roadmap

- Voice/IVR lessons (`providers.send_voice`) for low-literacy learners.
- Link `PhoneUser` to a full `accounts.User` so SMS progress counts toward
  mastery and certificates.
- Localised menus (Amharic / Afaan Oromo) — the `PhoneUser.language` field is
  already in place.
