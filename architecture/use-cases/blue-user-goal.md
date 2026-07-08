# Blue (User-Goal) Use Cases

Sea level — one actor, one sitting, one measurable goal. Fully-dressed.
V1 is manually assisted: where a step says "System", the Admin may perform it
by hand while the System records the result.

---

## UC-1 · Register a parcel request

- **Primary actor:** Sender · **Level:** User goal · **Scope:** Hulubul V1
- **Stakeholders & interests:** Sender — describe the parcel once, with minimum effort. Hulubul — capture a structured request.
- **Preconditions:** Sender reached Hulubul on an available channel; **a complete Sender profile exists** (created first via UC-13 if not).
- **Minimal guarantee:** Nothing is lost; a draft request with an ID is recorded.
- **Success guarantee:** A Parcel Request exists with the minimum data and status *Complete* (or *Needs clarification*).
- **Trigger:** Sender says they want to send a parcel.

**Main success scenario**
1. Sender provides the parcel intention and minimum data (origin, destination, parcel type, contact).
2. System identifies or creates the Sender.
3. System creates a Parcel Request and assigns a Request ID.
4. System checks completeness against the minimum-data rule.
5. System sets status *Complete*.

**Extensions**
- 4a. Data missing/unclear → System sets *Needs clarification* and requests the missing items; resume at 4.
- 1a. Sender is a returning party → System reuses known Sender data (manual in V1).

---

## UC-2 · Express preference for a transporter

- **Primary actor:** Sender · **Level:** User goal
- **Preconditions:** A request exists.
- **Minimal guarantee:** The stated preference is recorded against the request.
- **Success guarantee:** A usable Contact Point for the preferred transporter is linked to the request.
- **Trigger:** Sender names a preferred transporter/driver.

**Main success scenario**
1. Sender provides the preferred transporter's name and phone/contact.
2. System searches for an existing Contact Point.
3. System reuses it, or creates a new Contact Point (⊂ a Transporter Profile).
4. System validity-checks the Contact Point via a **round-robin ping + ack** (message the contact, await acknowledgement it works).
5. System links the preferred Contact Point to the request.
6. System **anonymously notifies the Transporter** that someone added them as a preference (no sender identity revealed).

**Extensions**
- 3a. A matching Transporter Profile exists → System links the Contact Point to that profile.
- 4a. No ack within the ping window → System marks the Contact Point for review.

---

## UC-3 · Match and choose a transporter

- **Primary actor:** Sender · **Level:** User goal
- **Preconditions:** Request is *Complete*; route and parcel data present.
- **Minimal guarantee:** Matching attempt and its result are recorded.
- **Success guarantee:** Sender has selected or ranked from up to 3 relevant options.
- **Trigger:** Request becomes ready for matching.

**Main success scenario**
1. System recommends up to 3 transporters by expressed preference, past experience, relevant route, and urgency/needed date.
2. System sets status *Options proposed*.
3. Sender reviews the options.
4. Sender selects or ranks a preferred option.
5. System records the selection/ranking.

**Extensions**
- 1a. No relevant transporter found → go to UC-10 (cascade / *No match*).
- 4a. Sender declines all options → System keeps request open or Sender cancels (UC-11).

---

## UC-4 · Forward request to a transporter

- **Primary actor:** Hulubul Admin · **Level:** User goal
- **Preconditions:** Sender selected/ranked an option; request summary complete enough to send.
- **Minimal guarantee:** The send attempt is logged against the Request ID.
- **Success guarantee:** The summarised request reached the selected transporter; status *Sent to transporter / Waiting for response*.
- **Trigger:** A selected transporter option exists.

**Main success scenario**
1. System assembles the request summary (same Request ID).
2. Admin sends the summary to the selected transporter / Contact Point via the channel.
3. System sets status *Sent to transporter* then *Waiting for response*.
4. System logs the communication (actor, channel, summary, timestamp).

**Extensions**
- 2a. Channel delivery fails → Admin retries or picks the next Contact Point.

---

## UC-5 · Respond to a transport request

- **Primary actor:** Transporter · **Level:** User goal
- **Preconditions:** Request was sent to the transporter.
- **Minimal guarantee:** The transporter's decision is recorded against the Request ID.
- **Success guarantee:** Status reflects *Accepted*, *Rejected*, or clarification requested; relevant parties notified.
- **Trigger:** Transporter reviews the request.

**Main success scenario**
1. Transporter reviews the summarised request.
2. Transporter accepts.
3. System sets status *Accepted* and notifies Sender (and Receiver if needed).

**Extensions**
- 2a. Transporter rejects → System sets *Rejected / Moving to next option* → UC-10.
- 2b. Transporter **asks for additional package info** before deciding → UC-6, then return to 1.
- 2c. No response within the wait time → reminder, then UC-10.

---

## UC-6 · Provide clarification / missing information

- **Primary actor:** Sender (Receiver may contribute delivery details) · **Level:** User goal
- **Preconditions:** Transporter asked for more info, or System detected missing data.
- **Minimal guarantee:** Added information is stored on the same Request ID.
- **Success guarantee:** Request is clear enough for an accept/reject decision; updated summary sent to the transporter.
- **Trigger:** A clarification request exists.

**Main success scenario**
1. System lists the missing/queried items.
2. Sender provides answers (and optionally photos/details).
3. System updates the request (same Request ID).
4. System re-sends the updated summary to the transporter.
5. System returns status to *Waiting for response*.

**Extensions**
- 2a. Delivery detail needed → Receiver provides address/contact.

---

## UC-7 · Plan pick-up and hand over the parcel

- **Primary actor:** Sender (with Transporter) · **Level:** User goal
- **Preconditions:** Transporter accepted; Sender confirmed to continue.
- **Minimal guarantee:** Any pick-up detail shared through Hulubul is recorded.
- **Success guarantee:** Parcel is handed over; status *Parcel picked up*.
- **Trigger:** Request is *Accepted*.

**Main success scenario**
1. Sender and Transporter agree place, time and contact person.
2. System records pick-up details and sets status *Pick-up planned*.
3. Sender hands the parcel to the Transporter.
4. Transporter confirms receipt.
5. System sets status *Parcel picked up* and notifies Sender (optionally Receiver).

**Extensions**
- 1a. Pick-up place unclear → Admin clarifies (home / meeting point / other).
- *. Detailed coordination may happen directly between Sender and Transporter; Hulubul keeps the minimum status.

---

## UC-8 · Coordinate and confirm delivery

- **Primary actor:** Transporter (with Receiver) · **Level:** User goal
- **Preconditions:** Parcel was picked up.
- **Minimal guarantee:** Delivery-related notes are recorded.
- **Success guarantee:** Delivery confirmed; status *Delivered*; who confirmed is recorded.
- **Trigger:** Parcel is in transit.

**Main success scenario**
1. Transporter coordinates delivery with Receiver (or Sender).
2. Receiver confirms availability / delivery details if needed.
3. Transporter delivers the parcel.
4. Transporter (or Receiver/Sender) confirms delivery.
5. System sets status *Delivered* and records who confirmed; notifies Sender.

**Extensions**
- 4a. Delivery not confirmed by any party → System keeps the request open and follows up until confirmation or manual closure.

---

## UC-9 · Close request and collect feedback

- **Primary actor:** Hulubul Admin · **Level:** User goal
- **Preconditions:** Delivery confirmed, or the request otherwise completed.
- **Minimal guarantee:** Request history is retained.
- **Success guarantee:** Status *Closed*; optional feedback stored.
- **Trigger:** Delivery is confirmed.

**Main success scenario**
1. System sets status *Closed*.
2. Admin optionally sends a feedback request.
3. Sender optionally gives feedback.
4. System stores feedback / internal note and retains request history.

---

## UC-10 · Cascade to the next transporter (exception)

- **Primary actor:** Hulubul Admin · **Level:** User goal
- **Preconditions:** Request was sent; a rejection, timeout, or no-match condition exists.
- **Minimal guarantee:** The cascade decision and reason are recorded.
- **Success guarantee:** Request forwarded to the next option, or marked *No match*; Sender informed.
- **Trigger:** Reject / no-response / no-option-left.

**Main success scenario**
1. System identifies the next-ranked transporter option.
2. Admin forwards the request to that option (→ UC-4).
3. System keeps the same Request ID and updated status.

**Extensions**
- 1a. No options remain → System sets *No match* and informs the Sender.
- 1b. No response case → System sends a reminder before advancing.

---

## UC-11 · Cancel a request (exception)

- **Primary actor:** Sender · **Level:** User goal
- **Preconditions:** Request exists and is not already closed.
- **Minimal guarantee:** Cancellation and any reason are recorded.
- **Success guarantee:** Status *Cancelled*; matching/cascade stopped; already-involved parties notified.
- **Trigger:** Sender no longer needs the transport.

**Main success scenario**
1. Sender informs Hulubul they want to stop the request.
2. System sets status *Cancelled* and stops matching/cascade.
3. System notifies parties already involved.
4. System stores the cancellation reason if available.

---

## UC-12 · Register / maintain a Transporter profile & routes

- **Primary actor:** Transporter · **Level:** User goal
- **Stakeholders & interests:** Transporter — be discoverable and matched relevantly. Hulubul — hold the profile+route data that matching (ADR-001 preconditions) needs.
- **Preconditions:** Transporter reached Hulubul on an available channel.
- **Minimal guarantee:** Whatever the Transporter provided is stored against a profile.
- **Success guarantee:** A Transporter Profile exists/updated with contact(s), routes, service type and frequency; profile status set.
- **Trigger:** Transporter wants to create or improve their profile (or is prompted after being added as a preference, UC-2).

**Main success scenario**
1. Transporter provides/updates identity, service type, and **routes + frequency**.
2. System creates/updates the Transporter Profile.
3. System attaches one or more **Contact Points** (⊂ the profile), each round-robin validity-checked (as UC-2 step 4).
4. System sets profile status (draft / validated / published, per the model).
5. System confirms the profile back to the Transporter.

**Extensions**
- 1a. A provisional Contact Point already exists (added by a Sender via UC-2) → System offers to attach/merge it (entity resolution, ADR-013).
- 3a. A Contact Point fails validity → stored but flagged, not used for matching.

---

## UC-13 · Register / maintain a party profile (Sender or Receiver)

- **Primary actor:** Sender **or** Receiver · **Level:** User goal
- **Stakeholders & interests:** Party — be known well enough to send/receive with minimum re-entry. Hulubul — satisfy the "complete profile" precondition (UC-1; ADR-011).
- **Preconditions:** Party reached Hulubul on an available channel (a Receiver may be created from a Sender's request data before establishing a live channel — ADR-011).
- **Minimal guarantee:** Provided data is stored against the party's profile.
- **Success guarantee:** A complete-enough profile exists (identity, contact, location/destination) for the party's role.
- **Trigger:** Party registers or updates their details (or is created as a required Receiver during UC-1).

**Main success scenario**
1. Party provides/updates identity, contact and location (Sender: origin locality; Receiver: destination locality).
2. System creates/updates the party profile.
3. System checks role-completeness (Sender: enough to start an order; Receiver: identity + destination — ADR-011).
4. System confirms the profile back to the party.

**Extensions**
- 1a. Receiver has no live channel yet → profile is created from Sender-supplied data; a live channel link is optional (ADR-011).
- 2a. Returning party → System reuses/merges known data (entity resolution, ADR-013).
