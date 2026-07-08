# Hulubul V1 — Project Statement

Source of direction: `Hulubul_Functional_Flow_Brief_Short_v0.4` (latest).
Background: Product Concept Brief v0.2, PDP strategic brief.

## Problem

Sending parcels between Moldova, the diaspora and other destinations runs on
informal channels — personal contacts, Facebook groups, WhatsApp, phone calls.
It works but is fragmented: senders hunt for someone on the right route and
re-explain the parcel each time; transporters receive incomplete, hard-to-track
requests. A plain list of transporters would just duplicate today's behaviour.

## What we are building

An **assisted parcel-request intermediation service**, not a directory. Hulubul
turns the intention *"I want to send a parcel"* into a structured **Parcel
Request**, matches it to relevant transporters, and carries the communication
through to pick-up and delivery. WhatsApp-first for the user; a structured
request (ID, data, status, minimum context) always exists in the background.

## V1 goal

Validate one assumption: that a structured request + guided communication
create real value for senders and transporters — **before** any advanced
automation. V1 may run **manually or semi-manually**; that is acceptable if it
produces learning and does not block the user.

## Actors

- **Sender** — starts the request, provides minimum parcel data. Main actor in V1.
- **Receiver** — informed / involved after acceptance or when delivery is coordinated.
- **Transporter** — accepts, rejects or asks details once a complete request reaches them. Single role in V1 (driver = dispatcher = manager).
- **Hulubul / Admin** — creates, checks, matches, forwards and updates the request. Operates the manual flow.

## Core object

The **Parcel Request** — Sender, Receiver, Parcel, route, status, communication
context. Supporting objects: **Contact Point** (a phone/contact for a
transporter, can exist without a full profile) and **Transporter Profile** (may
aggregate several Contact Points).

## Flow (happy path)

`Sender → Hulubul → Matching → Transporter → Hulubul → Sender/Receiver →
Pick-up → Delivery → Closure`

Create request → check completeness → capture preference → match (≤3 options) →
send to selected transporter → record accept/reject/clarify → plan pick-up →
hand over → coordinate delivery → confirm → close. Rejection/no-response
cascades to the next option; no option → *No match*.

## In scope (V1 must-have)

Structured Parcel Request with ID and status · Sender/Receiver/Transporter
roles · Contact Point vs Transporter Profile logic · simple matching ·
transporter preference · request forwarding · status tracking · minimum
communication context · manual/semi-manual admin support.

## Out of scope (post-V1)

Full WhatsApp API · conversational chatbot · automatic ranking / advanced
matching · transporter dashboard · driver/dispatcher separation · live tracking
· online payments · complex rating · disputes module · native mobile app ·
receiver-initiated requests.

## Success

Not features — **behaviour**: senders complete structured requests, transporters
respond to them, and requests move through the statuses to closure on a narrow
corridor, repeatedly.

## Open questions (from v0.4, blocking clarity)

Receiver-initiated requests in V1? · when to notify the Receiver · whether
Receiver data can wait until after acceptance · Contact Point as a separate
object · how to validate a Contact Point · number of options shown · manual vs
system-supported ranking · rejection-cascade automation · response wait time ·
exact data sent to the transporter · delivery-not-confirmed handling.
