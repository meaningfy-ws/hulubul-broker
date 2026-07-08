# Hulubul V1 — Use Cases (DRAFT)

Written in **Alistair Cockburn** style, fully-dressed. Grounded in the v0.4
Interaction Flow Matrix. To be confirmed in the interactive review.

## Goal levels (Cockburn colours)

- **White — summary level (kite ☁/🪁):** the whole service goal, spanning several user-goal use cases. See `white-summary.md`.
- **Blue — user-goal level (sea 🌊):** one actor, one sitting, one measurable goal. See `blue-user-goal.md`.
- Sub-function (fish/black) use cases are omitted in V1 — kept in component responsibilities instead.

## Primary actors

Sender · Receiver · Transporter · Hulubul Admin (operator). The **Admin** is the
active operator of the V1 manually-assisted flow; the System supports in the
background.

## Catalogue

| ID | Level | Use case | Primary actor |
|----|-------|----------|---------------|
| UC-0 | White | Intermediate a parcel delivery | Sender |
| UC-1 | Blue | Register a parcel request | Sender |
| UC-2 | Blue | Express preference for a transporter | Sender |
| UC-3 | Blue | Match and choose a transporter | Sender |
| UC-4 | Blue | Forward request to a transporter | Admin |
| UC-5 | Blue | Respond to a transport request | Transporter |
| UC-6 | Blue | Provide clarification / missing information | Sender |
| UC-7 | Blue | Plan pick-up and hand over the parcel | Sender |
| UC-8 | Blue | Coordinate and confirm delivery | Transporter |
| UC-9 | Blue | Close request and collect feedback | Admin |
| UC-10 | Blue | Cascade to the next transporter (exception) | Admin |
| UC-11 | Blue | Cancel a request (exception) | Sender |
| UC-12 | Blue | Register / maintain a Transporter profile & routes | Transporter |
| UC-13 | Blue | Register / maintain a party profile (Sender or Receiver) | Sender / Receiver |

Traceability: UC-1..UC-11 map to v0.4 matrix steps 1–13; UC-12..UC-13 are the
profile-lifecycle flows (ADR-002) that fill the ADR-001 preconditions. In the
autonomous direction (ADR-004) the "Admin" primary actor on UC-9/UC-10 is the
**System/agents**; a human Admin appears only on the exception/observability path.
