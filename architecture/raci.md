# Hulubul V1 — RACI Matrix (DRAFT)

Responsibility assignment across the brokerage flow. **R** = Responsible (does the
work), **A** = Accountable (owns the outcome — one per row), **C** = Consulted,
**I** = Informed.

**Note on the autonomous direction (ADR-004):** on success paths the **System /
Agents** are Responsible; the **Admin (human)** is Accountable in an oversight sense
and only becomes Responsible on exceptions/bugs (admin plane, ADR-007). "System"
below means the agents + deterministic core acting autonomously.

## Roles

Sender · Receiver · Transporter · **System/Agents** · **Admin** (human, exceptions
only)

## Brokerage flow (maps to use cases UC-1..UC-13)

| # | Activity (UC) | Sender | Receiver | Transporter | System/Agents | Admin |
|---|---------------|:--:|:--:|:--:|:--:|:--:|
| 1 | Register parcel request (UC-1) | R | I | – | A/R | I |
| 2 | Maintain own profile — Sender/Receiver (UC-13) | R | R | – | A/R | I |
| 3 | Maintain Transporter profile & routes (UC-12) | – | – | R | A/R | I |
| 4 | Express transporter preference (UC-2) | R | – | I (anon.) | A/R | I |
| 5 | Validate Contact Point — ping+ack (UC-2) | I | – | R (acks) | A/R | I |
| 6 | Match & recommend transporters (UC-3) | C | – | – | A/R | I |
| 7 | Choose / rank transporter (UC-3/4) | R | – | – | A | I |
| 8 | Forward request to transporter (UC-4) | I | – | I | A/R | I |
| 9 | Accept / reject / clarify (UC-5) | I | I | R | A | I |
| 10 | Provide clarification / package info (UC-6) | R | C | C | A/R | I |
| 11 | Plan pick-up & hand over (UC-7) | R | I | R | A/C | I |
| 12 | Coordinate & confirm delivery (UC-8) | I | R | R | A/C | I |
| 13 | Close request & collect feedback (UC-9) | C | I | I | A/R | I |
| 14 | Cascade to next transporter (UC-10) | I | – | I | A/R | I |
| 15 | Cancel request (UC-11) | R | I | I | A/R | I |
| 16 | Automated recovery / nudges (ADR-010) | I | I | I | A/R | I |
| 17 | Entity resolution — confirm merges (ADR-013) | C | C | C | A/R | I |
| 18 | Exception handling / controlled fixes (ADR-007) | I | I | I | C | **A/R** |
| 19 | Tune agent prompts & wiring (ADR-007) | – | – | – | I | **A/R** |

## Reading notes

- Rows 1–17: **System/Agents are A/R** — the autonomous core owns and does the work.
  Row 7 (final choice) and Row 9 (accept/reject) are **A**-only for System because the
  human party is Responsible for the actual decision; the System owns the outcome/record.
- Rows 18–19: the only places the **human Admin is Accountable/Responsible** — exceptions,
  bugs, and tuning. This is the intended boundary of human involvement (ADR-004).
- "–" = not involved. Anonymised involvement (Row 4) noted inline (ADR-009 / UC-2).
