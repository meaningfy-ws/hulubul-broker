# Hulubul V1 — Access-Control Model (companion to the model spec)

**Purpose.** Defines *who can access what* for the Hulubul V1 conceptual model
(`hulubul_v1_model_spec.md`). This is a **policy layer over the domain graph** — it
introduces no domain classes. Treat it as constraints/rules to enforce in the
application/authorization layer, not as schema classes on `Agent`.

---

## 1. Principles

1. **Relationship-based (ReBAC).** Access is never standing. A subject may act on a
   resource only because of a *path* from the subject to that resource through the
   participation graph (`Agent —playedBy⁻¹→ AgentInRole —(role edge)→ DeliveryRequest
   —references→ resource`). The `AgentInRole` instance is the grant.
2. **Instance-level, not field-level.** If a subject can open an instance, they see
   **all** its fields. There is no per-field hiding. Progressive disclosure is therefore
   achieved by controlling **which linked instances are reachable**, not by masking
   attributes.
3. **Disclosure by reachability.** "See the area but not the exact location before
   accepting" works only because the coarse `Area` and the exact location (`Address` or
   named `Place`) are *separate instances*. The subject reaches `Area` early and the exact
   location late. Same for contact: a relayed message thread is reachable before the
   counterpart's `Channel`. (Note: in the current diagrams pickup/drop-off point
   **directly** at the exact `SpatialObject`, so this separation requires the coarse-`Area`
   link flagged in §7.2 to actually be added.)
4. **Control-is-credential (implicit user/auth).** There is no `User`/`Account` class.
   A subject is authenticated by controlling a `Channel` with
   `validationStatus = valid`. "Who you are" is "which validated channel the message
   arrived on." (Holds only while Hulubul is bot-mediated.)
5. **Operator sees all.** There is no real coordinator role in the domain yet; model an
   `Operator`/admin account with unrestricted read/write, outside the domain classes.

---

## 2. Subjects (roles) and scope predicates

**Subjects:** `Operator`, `Sender`, `Receiver`, `Transporter`, `Public` (unauthenticated
or any logged-in agent acting outside a request).

**Scope predicates** (what "own"/"mine" unpacks to — all are graph paths, not flags):

| predicate | meaning |
|---|---|
| `self` | the resource *is* the subject's own `Agent`, or a `Channel`/`SpatialObject` hanging off it. No request on the path ⇒ ungated. |
| `party` | the subject plays `Sender` **or** `Receiver` in the `DeliveryRequest` that references the resource. |
| `sender` / `receiver` | the specific party role in that request. |
| `assigned` | the subject is the `Transporter` bound to that request (via `hasTransporter`) **or** has been recommended it. |
| `participant` | (for `Feedback`) the subject plays the `fromProvider` or `toRecipient` role of the feedback. |
| `public` | no path required. |

---

## 3. Lifecycle gates

Disclosure is gated on the `RequestStatus` of the `DeliveryRequest` on the access path
(the only lifecycle in the model). Two milestones matter:

- **Recommended gate** = status has reached `optionsProposed` (the request has been
  proposed/recommended to a transporter).
- **Accepted gate** = status has reached `accepted` (the transporter has committed).

**Gate semantics: reached-milestone, not numeric `≥`.** Because the lifecycle branches
(`rejected`, `cancelled`, `needsClarification` loops back), evaluate a gate as *"has the
request ever passed through milestone X"*, not *"current status ≥ X"*. Otherwise a
`cancelled`-after-`accepted` request would wrongly revoke a transporter's view
mid-handoff.

---

## 4. Access matrix (instance-level)

Each cell = "can the subject open an instance of this object type?" with the gate noted.
"—" = no access.

| Subject | Own profile (`Agent`) | Public catalog (`TransportService` + offering agent's `Channel` + reputation) | `DeliveryRequest` + parties | `Parcel` | Coarse `Area` (pickup/dropoff) | Exact `Address` | Counterpart `Agent` + `Channel` | Relayed message thread | `Feedback` |
|---|---|---|---|---|---|---|---|---|---|
| **Operator** | R/W all | R/W all | R/W all | R/W all | R all | R all | R all | R all | R all |
| **Sender** | R/W (self) | R (public) | R/W (own; create) | R/W (own) | R (own) | R (own) | R (receiver + assigned transporter) | R/W (with receiver + transporter) | R (participant) |
| **Receiver** | R/W (self) | R (public) | R (assigned) | R (assigned) | R (assigned) | R (assigned) | R (sender + assigned transporter) | R/W (with sender + transporter) | R (participant) |
| **Transporter** | R/W (self) | R + **W own listing** | R (fulfilled + recommended/assigned) | R (assigned) `@recommended` | R (assigned) `@recommended` | R (assigned) **`@accepted`** | R (sender/receiver) **`@accepted`** | R/W (with sender, **before** accept) | R (participant) |
| **Public** | — | R (public) | — | — | — | — | — | — | — |

---

## 5. Rules in plain language (source of truth for the matrix)

- **Everyone** can see their own profile (`self`, ungated).
- **Anyone (public)** can browse offered services, the offering agents' contact channels,
  and their **computed reputation**.
- **Sender** can initiate delivery requests and see their own past and current requests
  (including participating parties). The sender names the receiver; **sender and receiver
  can see each other and exchange messages.**
- **Transporter** can update their own service description and contact info. They can see
  the past requests they fulfilled and new open requests where they have been
  **recommended or assigned** (including participating parties). They can **exchange
  messages with the sender even before accepting**, but they learn the sender's/receiver's
  **details (name, contact, exact address) only after accepting**.
- **Receiver** can see their own profile and the requests they have been assigned to
  (including participating parties).
- **Operator** (admin) can see everything.

---

## 6. Feedback & reputation

- **Feedback (individual):** visible only to its **participants** — the agents playing
  its `fromProvider` or `toRecipient` roles — plus `Operator`. Not public.
- **Reputation (aggregate):** **public** and **derived** — computed from an agent's
  feedbacks, not stored on `Agent`. Model reputation as a *computed/read-only resource*,
  not a persisted attribute. Public visibility applies at least to service-offering
  agents (transporters).

---

## 7. Consequences / gaps the model must close

These are required for the rules above to be enforceable at instance level. They are
**not yet in the diagrams** — flag to Eugen.

1. **Relayed messaging object is missing.** "Message before contact is revealed" requires
   the platform to relay messages, i.e. a `Communication`/`MessageThread` instance that is
   reachable *before* the counterpart's `Channel`. Add such a class (participants, request
   link, messages) so "can message" and "can see contact" are separate permissions on
   separate objects.
2. **Coarse-area link on the request is missing.** Instance-level access cannot show "the
   area" while hiding "the exact location": pickup/drop-off point **directly** at the exact
   `SpatialObject` (`Address` or named `Place`), and the only coarse unit is reached
   *through* it (`Address.withinArea → Area`, `Place.withinArea → Area`). The
   `DeliveryRequest` (or `Parcel`) needs a **direct** coarse `Area` link
   (`hasPickUpArea` / `hasDropOffArea → Area`), separate from the exact location, so a
   pre-accept transporter reaches the `Area` but not the exact location. (This also serves
   matching: coarse supply / precise demand.)
3. **Reputation object.** Add a derived, public reputation resource distinct from the
   participant-private `Feedback`.
4. **Operator account** is outside the domain model — represent as an authorization role,
   not an `Agent` subtype.

---

## 8. Enforcement guidance (for the authorization layer)

- Keep the domain model describing *what is true*; put *who may see it* in a policy
  layer that queries the same graph (a ReBAC engine, or rules over the canonical store).
- Do **not** add `Permission`/`AccessRule`/`User` classes to the domain model.
- The disclosure gates read `DeliveryRequest.hasStatus`; ensure the status history (or a
  reached-milestone flag) is queryable, since gates are milestone-based, not
  current-value comparisons.
