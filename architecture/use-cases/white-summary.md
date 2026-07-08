# White (Summary) Use Cases

Kite level — the overall service goal that the blue use cases realise.

---

## UC-0 · Intermediate a parcel delivery

- **Scope:** Hulubul V1 service
- **Level:** Summary (white / kite)
- **Primary actor:** Sender
- **Supporting actors:** Receiver, Transporter, Hulubul Admin
- **Stakeholders & interests:**
  - *Sender* — wants the parcel sent with minimum effort, to a trusted/relevant transporter.
  - *Transporter* — wants complete, clear requests worth accepting.
  - *Receiver* — wants to know a parcel is coming and confirm receipt.
  - *Hulubul* — wants a structured request and enough context to learn whether intermediation adds value.
- **Precondition:** Sender can reach Hulubul through an available channel (WhatsApp/phone).
- **Minimal guarantee:** A structured Parcel Request exists with an ID and a status, whatever the outcome.
- **Success guarantee:** The parcel is picked up, delivered, confirmed, and the request is closed.
- **Trigger:** Sender expresses the intention to send a parcel.

### Main success scenario

1. Sender registers a parcel request *(UC-1)*.
2. Sender optionally expresses a transporter preference *(UC-2)*.
3. Sender is matched to relevant transporters and chooses one *(UC-3)*.
4. Admin forwards the request to the chosen transporter *(UC-4)*.
5. Transporter accepts the request *(UC-5)*.
6. Sender plans pick-up and hands over the parcel *(UC-7)*.
7. Transporter coordinates and confirms delivery *(UC-8)*.
8. Admin closes the request and collects feedback *(UC-9)*.

### Extensions

- 3a. No transporter accepts → cascade to next option, else *No match* *(UC-10)*.
- 5a. Transporter asks for clarification → Sender provides it *(UC-6)*, then return to 5.
- *a (any step). Sender no longer needs the transport → cancel *(UC-11)*.
