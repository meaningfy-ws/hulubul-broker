# Hulubul V1 — UML-Faithful Transcription & Specification

**Purpose.** A faithful transcription of the five Enterprise Architect UML diagrams
(2026-07-10 version) for the Hulubul V1 conceptual model, enriched with definitions,
alternative labels, design intentions, and constraints for each model element.

**Scope.** This document is a **specification**, not an implementation. It does **not**
prescribe how the model is encoded in LinkML (or any other formalism) — that is the job
of a downstream modelling agent. Datatypes, class names, attributes, cardinalities and
associations are reported **exactly as drawn**; where the diagram is ambiguous or
internally inconsistent it is flagged rather than resolved.

Access-control rules are in the companion file `hulubul_v1_access_control.md`.

**Status.** This spec supersedes the older `hulubul_v1_model.yaml`,
`hulubul_v1_concept_spec.md`, `hulubul_v1_class_diagram.mermaid`,
`hulubul_v1_transporter_service_model.md`, and
`hulubul_v1_conceptual_model_transcription.md`.

---

## 0. Reading conventions

- **Namespace / prefix.** All terms carry prefix `hlb:` in the diagrams.
- **Datatypes** are transcribed as drawn: `rdf:PlainLiteral` (text), `xsd:int`,
  `xsd:float`, `xsd:dateTime`, `xsd:anyURI`. No datatype has been re-mapped.
- **Cardinality.** `[0..1]` optional single · `[1]` required single · `[0..*]` optional
  many · `[1..*]` required many. An attribute drawn with **no** cardinality marker is
  reported as **required single `[1]`**; such cases are noted where they look suspicious.
- **Generalization** is written `Subtype ▷ Supertype`. **Abstract** classes are marked.
- **Definition**, **Alt labels**, **Intention**, and **Constraints/notes** are
  specification additions (not present in the diagram) intended to inform the modelling
  agent. Alt labels are candidate synonyms/`skos:altLabel` values.

The five source diagrams:
1. Feedback + roles.
2. DeliveryRequest hub (request, parcel, locations, status).
3. Agent + Channel + roles.
4. Spatial (SpatialObject / Address / Area / Place / GeoCoordinates).
5. Service layer (TransportService / ServiceOffer).

---

## 1. Parties and roles

### hlb:Agent
- **Definition.** An enduring party — a person or an organisation — that participates in
  Hulubul. It holds a stable identity, one or more communication channels, an optional
  main location, and may publish a standing transport service and play episodic roles.
- **Alt labels.** Party, Actor.
- **Intention.** The *enduring* half of the party-role pattern. Identity, channels and
  location live here and persist across any number of requests and roles. An Agent is
  never itself a Sender/Receiver/Transporter — it *plays* those roles via `hlb:AgentInRole`.

Attributes:

| attribute | datatype | card | definition | alt labels |
|---|---|---|---|---|
| hlb:name | rdf:PlainLiteral | [1] | Human-readable name of the party. | fullName, title |
| hlb:identifier | rdf:PlainLiteral | [1] | Stable unique identifier of the agent within Hulubul. | id, agentId |
| hlb:description | rdf:PlainLiteral | [0..1] | Free-text description of the party. | note, bio |

Associations:

| association | target | card | definition | alt labels |
|---|---|---|---|---|
| hlb:hasContactPoint | hlb:Channel | [0..*] | Communication channels through which the agent can be reached and, when validated, authenticated. | hasChannel |
| hlb:hasMainContactPoint | hlb:Channel | [0..1] | The agent's primary/default channel; also the trusted login channel. | hasMainChannel, primaryChannel |
| hlb:hasMainLocation | hlb:Address | [0..1] | The agent's principal location. | mainLocation, basedAt |
| hlb:providesService | hlb:TransportService | [0..1] | The standing, request-agnostic transport offering published by this agent (present only for transporters). | offersService |

> **Note (edge naming).** The channel associations are still labelled `hasContactPoint`
> / `hasMainContactPoint` even though the target class was renamed `Channel`. Reported
> as-drawn; a coherent rename to `hasChannel` / `hasMainChannel` is offered as an alt
> label only.

### hlb:AgentInRole  *(abstract)*
- **Definition.** The episodic, situation-dependent role an Agent plays within a specific
  interaction; a reified *participation*. Anti-rigid: the same Agent plays different roles
  across different requests, and a role instance exists only in the context of a request
  execution.
- **Alt labels.** Participation, Role, RoleAssignment.
- **Intention.** This instance **is** the participation (CPSV-AP reified-participation
  reading). There is deliberately **no** stored link from a standing `TransportService`
  to a `DeliveryRequest`; the only binding between an agent's offering and a concrete
  request is the `Transporter` role instance realised for that request.

Associations:

| association | target | card | definition | alt labels |
|---|---|---|---|---|
| hlb:playedBy | hlb:Agent | [1] | The enduring agent enacting this role. | enactedBy, heldBy |
| hlb:hasAltContactPointInRole | hlb:Channel | [0..1] | An alternative channel to use for this participation, overriding the agent's default. | roleChannel |

Subtypes: `hlb:Transporter`, `hlb:Sender`, `hlb:Receiver`.

### hlb:Transporter  ▷ hlb:AgentInRole
- **Definition.** The role of the agent that carries the parcel(s) for a delivery request.
- **Alt labels.** Carrier, Courier.
- No own attributes.

### hlb:Sender  ▷ hlb:AgentInRole
- **Definition.** The role of the agent that initiates a delivery request and hands over
  the parcel(s). The sender also names the receiver.
- **Alt labels.** Consignor, Shipper.
- No own attributes.

### hlb:Receiver  ▷ hlb:AgentInRole
- **Definition.** The role of the agent intended to take delivery of the parcel(s).
- **Alt labels.** Consignee, Recipient.

| attribute | datatype | card | definition | alt labels |
|---|---|---|---|---|
| hlb:deliveryNote | rdf:PlainLiteral | [0..1] | A note from or for the receiver regarding delivery (e.g. handover instructions). | dropNote |

### hlb:Feedback
- **Definition.** A reified rating and/or comment left by one participation about another,
  optionally scoped to a delivery request. Feedback is the raw material from which an
  agent's public reputation is computed.
- **Alt labels.** Rating, Review, Testimonial.
- **Intention.** Attached to `AgentInRole` (the participation), **not** to `Agent`
  directly — you rate a party *as they acted in a given role/request*, not globally.
  Individual feedback is private to its two participants; only aggregate reputation is
  public (see access-control doc).

| attribute | datatype | card | definition | alt labels |
|---|---|---|---|---|
| hlb:rating | xsd:int | [0..1] | Numeric score. | score, stars |
| hlb:comment | rdf:PlainLiteral | [0..1] | Free-text remark. | remark, reviewText |

Associations:

| association | target | card | definition | alt labels |
|---|---|---|---|---|
| hlb:fromProvider | hlb:AgentInRole | [1] | The participation that authored the feedback. | author, ratedBy |
| hlb:toRecipient | hlb:AgentInRole | [1] | The participation the feedback is about. | subject, ratee |
| hlb:aboutRequest | hlb:DeliveryRequest | [0..1] | The delivery request the feedback concerns. | forRequest |

---

## 2. The delivery transaction

### hlb:DeliveryRequest
- **Definition.** The central transaction of Hulubul: a request to move one or more
  parcels from a pickup location to a drop-off location, carrying its participants,
  status, and lifecycle timestamps.
- **Alt labels.** Transport Request, Shipment Request, ParcelRequest *(former name)*.
- **Intention.** The hub that ties sender, receiver, transporter, parcels, locations and
  status together. Its `RequestStatus` is the **only** lifecycle in the model and is what
  all access-control disclosure gates read.

Attributes:

| attribute | datatype | card | definition | alt labels |
|---|---|---|---|---|
| hlb:requestNote | rdf:PlainLiteral | [0..*] | Free-text notes attached to the request. | note |
| hlb:preferredPeriod | rdf:PlainLiteral | [0..1] | The requester's preferred timeframe (orientative, free text). | preferredTime, timeWindow |
| hlb:created | xsd:dateTime | [1] | When the request was created. | createdAt |
| hlb:updated | xsd:dateTime | [1] | When the request was last modified. | updatedAt |
| hlb:closed | xsd:dateTime | [1] ⚠ | When the request was closed/terminated. | closedAt |

> ⚠ **Flag.** `closed` is drawn without a cardinality marker (⇒ required). An open
> request would have no close time, so `[0..1]` is more plausible. Confirm.

Associations:

| association | target | card | definition | alt labels |
|---|---|---|---|---|
| hlb:hasSender | hlb:Sender | [1] | The sender participation for this request. | sender |
| hlb:hasReceiver | hlb:Receiver | [1] | The primary receiver participation. | receiver |
| hlb:hasTransporter | hlb:Transporter | [0..1] | The assigned transporter participation, once one is selected. | transporter |
| hlb:hasStatus | hlb:RequestStatus | [1] | Current lifecycle status. | status |
| hlb:hasDeliveryItem | hlb:Parcel | [1..*] | The parcel(s) to be delivered. | items, parcels |
| hlb:hasPickUpLocation | hlb:SpatialObject | [1] | Where the parcel(s) are collected — an `Address` or a named `Place`. | pickupLocation, origin |
| hlb:hasDropOffLocation | hlb:SpatialObject | [1] | Where the parcel(s) are delivered — an `Address` or a named `Place`. | dropoffLocation, destination |
| hlb:hasAltDropOffLocation | hlb:SpatialObject | [0..1] | An alternative drop-off location (`Address` or `Place`). | altDropoff |

> **Note (target reverted to `SpatialObject`).** Pickup / drop-off / alt-drop-off point at
> the abstract `SpatialObject` (diagram 2) so a location can be either a precise `Address`
> **or** a named `Place` (e.g. a petrol station on a highway). The **intended range is
> `{Address, Place}`, not `Area`** — an `Area` is too coarse to be a pickup/drop-off point.
> This is a range constraint the diagram cannot express (it just draws `SpatialObject`);
> the modelling agent should restrict the range to `Address ∪ Place`.
>
> **Flag (cross-diagram conflict).** `hasAltDropOffLocation` is drawn from **two different
> sources**: in diagram 2 from `DeliveryRequest → SpatialObject` (reported here), and in
> diagram 3 from `Receiver → Address [0..1]`. These cannot both be the same edge (and the
> targets differ). Decide the single owner: request-level (this request's fallback
> drop-off), receiver-level (a standing default for that receiver), or parcel-level
> (alongside `hasAltReceiver`). Confirm.

### hlb:Parcel
- **Definition.** A physical item to be delivered as part of a request.
- **Alt labels.** Package, Item, Shipment Item.

| attribute | datatype | card | definition | alt labels |
|---|---|---|---|---|
| hlb:declaredContent | rdf:PlainLiteral | [1] | The sender's declared description of contents. | contents |
| hlb:photoURL | xsd:anyURI | [0..*] | URLs of photos of the parcel. | photo, imageURL |
| hlb:weightKg | xsd:float | [0..1] | Weight in kilograms. | weight |
| hlb:dimensions | rdf:PlainLiteral | [0..1] | Free-text dimensions (e.g. "30×20×10 cm"). | size |

Associations:

| association | target | card | definition | alt labels |
|---|---|---|---|---|
| hlb:hasAltReceiver | hlb:Receiver | [0..1] | An alternative receiver for this specific parcel. | altReceiver |

### hlb:RequestStatus  «enumeration»
Lifecycle states of a `DeliveryRequest`. Order below is the intended lifecycle
progression (used by access gates as *reached-milestone*, not numeric comparison).

| value | definition |
|---|---|
| hlb:new | Just created; not yet triaged. |
| hlb:needsClarification | Awaiting more information from the sender. |
| hlb:complete | Fully specified and ready to be matched. |
| hlb:optionsProposed | One or more transporters have been proposed/recommended. |
| hlb:waitingResponse | Awaiting a party's response to proposed options. |
| hlb:accepted | A transporter has committed; the job is on. |
| hlb:rejected | The proposed option(s) were declined. |
| hlb:pickUpPlanned | Pickup has been scheduled. |
| hlb:pickedUp | Parcel(s) collected. |
| hlb:delivered | Parcel(s) delivered. |
| hlb:cancelled | Request cancelled. |

> **Access-gate anchors.** `optionsProposed` = "recommended" gate; `accepted` =
> "accepted" gate (see access-control doc).

---

## 3. Channels (contact + identity)

### hlb:Channel
- **Definition.** A communication channel bound to a single agent — the endpoint through
  which the agent is reached and, when validated, authenticated. In Hulubul's
  bot-mediated V1, control of a **validated** channel *is* the credential; there is no
  separate `User`/`Account` class.
- **Alt labels.** ContactPoint *(former name)*, Contact Channel, Account, Principal.
- **Intention.** Unifies "how to reach you" and "how we identify/trust you" because in a
  messaging-bot architecture they are the same fact (control of the Telegram/WhatsApp
  account). **This unification holds only while Hulubul is purely bot-mediated.** If a web
  login or a reach-only-but-not-login channel is ever added, identity (`Account`) should
  be re-split from reachability (`Channel`).

Attributes:

| attribute | datatype | card | definition | alt labels |
|---|---|---|---|---|
| hlb:alias | rdf:PlainLiteral | [0..1] | Human label for the channel (e.g. "mum's WhatsApp"). | label, nickname |
| hlb:systemID | rdf:PlainLiteral | [1] | Provider/platform-issued identifier (e.g. Telegram chat/user id). | externalId, accountId |
| hlb:email | rdf:PlainLiteral | [0..1] | Email address, when the medium is email. | emailAddress |
| hlb:telephone | rdf:PlainLiteral | [0..1] | Phone number, when the medium is phone-based. | phone, msisdn |
| hlb:description | rdf:PlainLiteral | [0..1] | Free-text description. | note |

Associations:

| association | target | card | definition | alt labels |
|---|---|---|---|---|
| hlb:hasMedium | hlb:Medium | [1] | The medium/platform of this channel. | medium, platform |
| hlb:validationStatus | hlb:ChannelValidationStatus | [1] | Whether control of the channel has been verified (a `valid` channel is a usable login). | verificationStatus |

> **Note (handle bundle).** `Channel` carries `systemID` + `email` + `telephone` as
> parallel handle slots even though `hasMedium` already disambiguates the medium.
> Reported as-drawn. A candidate simplification (single `handle` interpreted per
> `hasMedium`, keeping `systemID` only for the platform-internal id) is left to the
> modelling agent / Eugen to decide — not applied here.
>
> **Note (identity binding).** No reverse `Channel → Agent [1]` binding is drawn; the only
> link is `Agent —hasContactPoint→ Channel`. If every channel must belong to exactly one
> agent, an explicit binding is worth adding. Flagged, not applied.

### hlb:Medium  «enumeration»
| value | definition |
|---|---|
| hlb:GSM | Mobile phone / SMS / voice. |
| hlb:WhatsApp | WhatsApp messaging. |
| hlb:Telegram | Telegram messaging. |
| hlb:Viber | Viber messaging. |
| hlb:email | Email. |

### hlb:ChannelValidationStatus  «enumeration»
| value | definition |
|---|---|
| hlb:valid | Control verified; usable as a trusted login. |
| hlb:invalid | Verification failed or channel unreachable. |
| hlb:needsReview | Not yet verified; contact-only until validated. |

---

## 4. Spatial model (GeoSPARQL-aligned)

### hlb:SpatialObject  *(abstract)*
- **Definition.** Root of the spatial hierarchy (aligned to `geo:SpatialObject`).
  Anything with spatial identity that may carry a geometry.
- **Alt labels.** Spatial Thing, Location.
- **Intention.** `Address`, `Area` and `Place` are the three subtypes; a concrete geometry
  is attached by **composition** via `hasCoordinates` (GeoSPARQL `hasGeometry` reading),
  **not** by subtyping. Keeping the coarse `Area` and the precise `Address` as *separate
  instances* is load-bearing for access control (disclosure by reachability).

| attribute | datatype | card | definition | alt labels |
|---|---|---|---|---|
| hlb:comment | rdf:PlainLiteral | [1] ⚠ | Free-text remark/annotation on the spatial object. | note, annotation |

> ⚠ **Flag (two changes since the last version).** (a) The former `name [0..1]` on
> `SpatialObject` is **gone**; a name now lives only on `Place` (as `name [0..1]`).
> (b) The new `comment` is drawn **without** a cardinality marker (⇒ required). A
> mandatory free-text comment on *every* spatial object is implausible — `[0..1]` is far
> more likely. Confirm.

Associations:

| association | target | card | definition | alt labels |
|---|---|---|---|---|
| hlb:hasCoordinates | hlb:GeoCoordinates | [0..1] | The point geometry of this spatial object. | hasGeometry, coordinates |

Subtypes: `hlb:Address`, `hlb:Area`, `hlb:Place`.

### hlb:Address  ▷ hlb:SpatialObject
- **Definition.** A precise, pin-level postal address.
- **Alt labels.** Postal Address, Street Address.

| attribute | datatype | card | definition | alt labels |
|---|---|---|---|---|
| hlb:number | rdf:PlainLiteral | [1] | House/building number. | houseNumber |
| hlb:street | rdf:PlainLiteral | [1] | Street name. | streetName |
| hlb:postCode | rdf:PlainLiteral | [1] | Postal code. | zip, postalCode |

Associations:

| association | target | card | definition | alt labels |
|---|---|---|---|---|
| hlb:withinArea | hlb:Area | [1] | The coarse administrative area this address falls within. | inArea, withinPlace *(former target: Place)* |

### hlb:Area  ▷ hlb:SpatialObject
- **Definition.** A coarse administrative or geographic unit (locality, county, state,
  country) forming a nested containment hierarchy. This is the "coarse supply / precise
  demand" unit: transporter service offers and matching operate on `Area`, while exact
  pickup/delivery use `Address`.
- **Alt labels.** Region, Locality, Administrative Area, Zone.
- **Intention.** **New class** (split out of the former single `Place`). `Address` sits
  `withinArea` an `Area`, and an `Area` may recursively sit `withinArea` a larger `Area`
  (locality → county → state → country), giving containment for coarse matching without a
  separate hierarchy class. `ServiceOffer` served-areas are `Area`s.

| attribute | datatype | card | definition | alt labels |
|---|---|---|---|---|
| hlb:locality | rdf:PlainLiteral | [0..1] | Town/city/locality name. | city, town |
| hlb:county | rdf:PlainLiteral | [0..1] | County/district (raion). | district, raion |
| hlb:country | rdf:PlainLiteral | [0..1] | Country name. | countryName |
| hlb:state | rdf:PlainLiteral | [0..1] | State/region within country. | region, province |

Associations:

| association | target | card | definition | alt labels |
|---|---|---|---|---|
| hlb:withinArea | hlb:Area | [0..*] | Larger area(s) that recursively contain this area. | inArea, parentArea |

> **Note (changes since last version).** `Area` did not exist before; its attributes were
> carried by the old `Place`. The former `Place.countryCode` is **dropped** entirely (only
> `country` remains). The reflexive `withinArea` is drawn `[0..*]` — an area within
> multiple larger areas is unusual (normally one parent); confirm whether `[0..1]` is
> intended.

### hlb:Place  ▷ hlb:SpatialObject
- **Definition.** A named point/place of interest (e.g. a landmark, depot, pickup point),
  identified and typed, sitting within an `Area`. Distinct from the coarse `Area` and from
  the precise postal `Address`.
- **Alt labels.** Named Place, Point of Interest, Landmark.
- **Intention.** **Redefined** — `Place` no longer carries administrative attributes
  (those moved to `Area`). It is now a *named, typed* location reachable within an `Area`.
  Nothing in the five diagrams currently *references* `Place` (no request, parcel, agent
  or service points at it); it stands as an available spatial concept whose consumers are
  yet to be wired. Flag to confirm its intended use.

| attribute | datatype | card | definition | alt labels |
|---|---|---|---|---|
| hlb:name | rdf:PlainLiteral | [0..1] | Human-readable name of the place. | label, placeName |
| hlb:hasIdentifier | rdf:PlainLiteral | [1] | Identifier of the place (e.g. gazetteer id). | placeId, gazetteerId |
| hlb:hasType | rdf:PlainLiteral | [1] | Type of the place (e.g. depot, landmark, pickup point). | placeType |

Associations:

| association | target | card | definition | alt labels |
|---|---|---|---|---|
| hlb:withinArea | hlb:Area | [0..1] | The area this place sits within. | inArea |

### hlb:GeoCoordinates
- **Definition.** A WGS84 latitude/longitude point — the geometry attached to a spatial
  object (GeoSPARQL `geo:Geometry` analogue).
- **Alt labels.** Coordinates, Point, Geometry, LatLong.
- **Intention.** A composed value object (reached only via `hasCoordinates`), **not** a
  subtype of `SpatialObject`. Point-only today; if area matching needs polygons/bboxes,
  extend here rather than by subtyping.

| attribute | datatype | card | definition | alt labels |
|---|---|---|---|---|
| hlb:latitude | xsd:float | [1] | WGS84 latitude. | lat |
| hlb:longitude | xsd:float | [1] | WGS84 longitude. | lon, lng |

---

## 5. Service / offering layer

### hlb:TransportService
- **Definition.** A standing, request-agnostic offering published by a transporter agent,
  declaring what it carries (service types) and its base (pickup) and destination
  (delivery) service areas, each with an orientative frequency.
- **Alt labels.** Transporter Profile *(former concept)*, Service Offering, Offer Profile.
- **Intention.** The *standing capability* layer of the three-layer transporter split
  (Agent · TransportService · episodic Transporter role). It exists, geocodes and is
  matchable **before** any request. It carries **no** link to any `DeliveryRequest`.

| attribute | datatype | card | definition | alt labels |
|---|---|---|---|---|
| hlb:serviceTitle | rdf:PlainLiteral | [1] | Short title of the offering. | title |
| hlb:description | rdf:PlainLiteral | [1] | Description of the offering. | summary |

Associations:

| association | target | card | definition | alt labels |
|---|---|---|---|---|
| hlb:serviceType | hlb:ServiceType | [1..*] | What the service carries (people and/or parcels). | offers |
| hlb:hasBaseArea | hlb:ServiceOffer | [1..*] | Pickup footprint — areas (with frequency) where the transporter can collect. | baseArea, pickupArea |
| hlb:hasDestinationArea | hlb:ServiceOffer | [1..*] | Delivery reach — areas (with frequency) the transporter serves as destinations. | destinationArea, deliveryArea |

### hlb:ServiceOffer
- **Definition.** A value object pairing a served area with an orientative frequency. The
  **same** shape is used for both base and destination offers; direction is given by which
  association (`hasBaseArea` vs `hasDestinationArea`) it sits under, not by a flag.
- **Alt labels.** Service Area Offer, Area Offer, ServiceLocationSchedule *(former name)*.
- **Intention.** Return capacity comes for free: a transporter that also collects at a
  destination simply lists that area in *both* base and destination — no `bidirectional`
  flag. Cartesian pairing (any base with any destination) is accepted for V1's informal,
  roughly single-hub transporters; escalate to explicit `fromArea → toArea` lanes only if
  a transporter needs base-pair-specific routing.

| attribute | datatype | card | definition | alt labels |
|---|---|---|---|---|
| hlb:description | rdf:PlainLiteral | [1] | Free-text description of the offer. | note |

Associations:

| association | target | card | definition | alt labels |
|---|---|---|---|---|
| hlb:withinArea | hlb:Area | [1] | The served administrative area. | servesArea, area |
| hlb:withFrequency | hlb:Frequency | [1] | How often the transporter is in/through the area (orientative). | frequency, hasFrequency *(former name)* |

### hlb:ServiceType  «enumeration»
| value | definition |
|---|---|
| hlb:peopleTransport | Carries people. |
| hlb:parcelTransport | Carries parcels. |

### hlb:Frequency  «enumeration»
Orientative — a coarse human-coordination label, **not** a timetable/RRULE.

| value | definition |
|---|---|
| hlb:daily | About once a day. |
| hlb:weekly | About once a week. |
| hlb:biweekly | About twice a week. *(confirm intended sense — see note)* |
| hlb:fortnightly | About once every two weeks. |
| hlb:monthly | About once a month. |

> **Note.** `biweekly` is ambiguous in English (twice-a-week vs every-two-weeks). Since
> `fortnightly` already covers every-two-weeks, `biweekly` presumably means
> **twice-weekly** here — confirm; `twiceWeekly` would remove the ambiguity.

---

## 6. Properties observed on more than one class

Reported for the modelling agent's awareness — these names recur and may denote the same
property:

- **hlb:name** — on `Agent` (required) and `Place` (optional). No longer on `SpatialObject`.
- **hlb:comment** — on `SpatialObject`; **hlb:description** — on `Agent`, `Channel`,
  `TransportService`, `ServiceOffer`; **hlb:deliveryNote** (`Receiver`),
  **hlb:requestNote** (`DeliveryRequest`): a family of free-text annotation slots — align
  if a shared annotation property is desired.
- **hlb:withinArea** — used by `Address → Area [1]`, `Place → Area [0..1]`,
  `Area → Area [0..*]` (reflexive), and `ServiceOffer → Area [1]`; all target `Area` with
  the same "is within this area" semantics.
- **Location associations** — `hasPickUpLocation`, `hasDropOffLocation`,
  `hasAltDropOffLocation` (request) target the abstract `SpatialObject` (intended range
  `Address ∪ Place`); `hasMainLocation` (agent, diagram 3) targets `Address`.
  ⚠ Minor inconsistency: request locations accept a `Place`, but the agent's main location
  is drawn as `Address`-only — align if an agent's base can also be a named `Place`.
- **Channel-valued associations** — `hasContactPoint`, `hasMainContactPoint`,
  `hasAltContactPointInRole` all target `Channel`.
- **hlb:identifier** (`Agent`) vs **hlb:hasIdentifier** (`Place`) — distinct names for
  identifier-like properties; align if a shared property is desired.

Natural top-level entities: `Agent`, `DeliveryRequest`, `TransportService`.

---

## 7. Design intentions (context for the model)

1. **Party-role pattern.** `Agent` (enduring) plays episodic roles via `AgentInRole`
   (= reified participation). No stored `TransportService → DeliveryRequest` link.
2. **Three-layer transporter split.** Agent · standing `TransportService` · episodic
   `Transporter` role.
3. **Service areas, not routes.** Base + destination `ServiceOffer`s over `Area`;
   frequency orientative; matching is coarse-supply/precise-demand.
4. **Matching rule.** the `Area` containing `request.pickup` (the location's `withinArea`,
   whether it is an `Address` or a `Place`) falls within some base offer's `Area` **AND**
   the `Area` containing `request.dropoff` falls within some destination offer's `Area`,
   tested via `Area.withinArea` containment.
5. **GeoSPARQL alignment.** `SpatialObject → {Address, Area, Place}` subtypes;
   `GeoCoordinates` composed via `hasCoordinates`. Coarse `Area` (nested via reflexive
   `withinArea`) vs precise `Address` vs named `Place`.
6. **Channel = contact + identity.** Control of a validated channel is the credential;
   user/auth are implicit. Bot-mediated-only assumption.
7. **Controlled vocabularies.** Enumerations (`Medium`, `Frequency`, `ServiceType`,
   `RequestStatus`, validation statuses) are candidates for SKOS-backed controlled codes
   as the model matures (CPSV-AP lesson) — a modelling choice, not decided here.

---

## 8. Open items to confirm with Eugen

1. `hasAltDropOffLocation` owner: drawn from **`DeliveryRequest`** (diagram 2) **and**
   **`Receiver`** (diagram 3) — pick one (request- / receiver- / parcel-level).
2. `DeliveryRequest.closed` cardinality: `[1]` (as drawn) or `[0..1]`?
3. `SpatialObject.comment` cardinality: `[1]` (as drawn) or `[0..1]`? (A mandatory comment
   on every spatial object is implausible.)
4. `Area.withinArea` (reflexive) cardinality: `[0..*]` (as drawn) or `[0..1]` (one parent)?
5. `Place`'s role: it is defined (name / hasIdentifier / hasType, within an `Area`) but
   **nothing references it** in the five diagrams — confirm its intended consumers.
6. `Channel` handle bundle: keep `systemID`+`email`+`telephone`, or collapse to a single
   handle + `hasMedium`?
7. `Frequency.biweekly` semantics (twice-weekly vs fortnightly)?
8. Add a `Channel → Agent [1]` identity binding?
9. Should `hasPickUpLocation`/`hasDropOffLocation` range be explicitly restricted to
   `Address ∪ Place` (excluding `Area`), since the diagram can only draw the abstract
   `SpatialObject`?
10. **Access-control dependency:** pickup / drop-off target the **exact location**
   (`Address` or `Place`), with **no** direct coarse-`Area` link on the request. Add
   `hasPickUpArea`/`hasDropOffArea → Area` on the request (separate from the exact
   location) so a pre-accept transporter can reach the `Area` but not the exact location.
   Required for instance-level progressive disclosure — see `hulubul_v1_access_control.md`.
