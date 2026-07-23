"""Graph identifier generation service for deterministic UUID management.

Implements Task 12 (original 3.3) deterministic graph identifier generation per plan.md.

Provides:
- Session IDs (random UUID4 per call, one per request intake flow)
- Enduring Agent IDs (stable UUID5 from Sender/Receiver identifier, reusable across requests)
- Request-scoped identifiers (request, sender role, receiver role, parcel, places)
- Sparse allocation (only allocate IDs for entities actually present in the request)

All UUIDs are prefixed per design DEC-010: req-, ag-, s-, r-, p-, pl-,
urn:uuid:, urn:hulubul:phase1:receiver:
All outputs are strings in RFC 4122 UUID format.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import NAMESPACE_DNS, NAMESPACE_URL, uuid4, uuid5

from hulubul.core.models.operational.intake import GraphIdentifiers

__all__ = [
    "enduring_agent_id",
    "generate_delivery_id",
    "generate_request_id",
    "generate_session_id",
    "new_graph_identifiers",
]


def generate_session_id() -> str:
    """Generate a new random session UUID4.

    Returns:
        str: A new UUID4 in string format. Each call produces a unique ID.

    Example:
        >>> session_id = generate_session_id()
        >>> session_id  # doctest: +SKIP
        'a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d'
    """
    return str(uuid4())


def generate_request_id(parcel_intent: str, receiver_id: str) -> str:
    """Generate a deterministic request UUID5.

    Uses a stable namespace to ensure identical inputs always produce the same ID.

    Args:
        parcel_intent: The intent or description of the parcel (e.g., "deliver_package")
        receiver_id: The unique identifier of the receiver

    Returns:
        str: A UUID5 in string format. Identical inputs always produce the same ID.

    Example:
        >>> id1 = generate_request_id("deliver_package", "receiver_123")
        >>> id2 = generate_request_id("deliver_package", "receiver_123")
        >>> id1 == id2
        True
    """
    seed = f"request:{parcel_intent}:{receiver_id}"
    return str(uuid5(NAMESPACE_DNS, seed))


def generate_delivery_id(request_id: str, transporter_id: str) -> str:
    """Generate a deterministic delivery UUID5.

    Uses a stable namespace to ensure identical inputs always produce the same ID.

    Args:
        request_id: The unique identifier of the request
        transporter_id: The unique identifier of the transporter

    Returns:
        str: A UUID5 in string format. Identical inputs always produce the same ID.

    Example:
        >>> id1 = generate_delivery_id("request_xyz", "transporter_001")
        >>> id2 = generate_delivery_id("request_xyz", "transporter_001")
        >>> id1 == id2
        True
    """
    seed = f"delivery:{request_id}:{transporter_id}"
    return str(uuid5(NAMESPACE_DNS, seed))


def enduring_agent_id(stable_identifier: str) -> str:
    """Generate a stable enduring Agent ID (Sender or Receiver identity).

    Uses UUID5 to ensure the same identifier always produces the same Agent ID.
    This ID persists across requests for trusted Senders and stable-identified Receivers.

    Args:
        stable_identifier: The stable identity string (e.g., Sender phone, Receiver email)

    Returns:
        str: An Agent ID with `ag-` prefix followed by UUID5 hex.

    Example:
        >>> id1 = enduring_agent_id("sender@example.com")
        >>> id2 = enduring_agent_id("sender@example.com")
        >>> id1 == id2 and id1.startswith("ag-")
        True
    """
    uuid_part = str(uuid5(NAMESPACE_URL, stable_identifier))
    return f"ag-{uuid_part}"


def new_graph_identifiers(
    *,
    actor_id: str,
    receiver_stable_id: str | None,
    include_receiver: bool = False,
    include_parcel: bool = False,
    include_pickup: bool = False,
    include_drop_off: bool = False,
    uuid_factory: Callable[[], str] = generate_session_id,
) -> GraphIdentifiers:
    """Allocate graph node identifiers in deterministic order (sparse).

    Allocation order: request → sender → receiver (if present) → parcel (if present)
    → pickup place (if present) → drop-off place (if present).

    Each entity gets a prefixed UUID4 from uuid_factory. Places also get a urn:uuid: identifier.
    Name-only Receiver (no stable_id) gets a request-scoped URN instead of an enduring Agent ID.

    Args:
        actor_id: The actor (Sender) stable identifier (for enduring agent ID)
        receiver_stable_id: Receiver stable identifier (or None for name-only Receiver)
        include_receiver: Whether to allocate Receiver role ID
        include_parcel: Whether to allocate Parcel ID
        include_pickup: Whether to allocate pickup Place ID
        include_drop_off: Whether to allocate drop-off Place ID
        uuid_factory: Function to generate UUIDs (default: generate_session_id)

    Returns:
        GraphIdentifiers: Partially populated model with allocated IDs; unallocated fields are None.
    """
    identifiers: dict[str, str | None] = {}

    # 1. Request ID (always allocated)
    identifiers["request_id"] = f"req-{uuid_factory()}"

    # 2. Sender role ID (always allocated if actor_id present)
    identifiers["sender_id"] = f"s-{uuid_factory()}"
    identifiers["sender_agent_id"] = enduring_agent_id(actor_id)

    # 3. Receiver role ID and agent ID (sparse)
    if include_receiver:
        identifiers["receiver_id"] = f"r-{uuid_factory()}"
        if receiver_stable_id:
            identifiers["receiver_agent_id"] = enduring_agent_id(receiver_stable_id)
            identifiers["receiver_agent_identifier"] = receiver_stable_id
        else:
            # Name-only Receiver: request-scoped URN instead of enduring agent ID
            request_scoped_urn = f"urn:hulubul:phase1:receiver:{uuid_factory()}"
            identifiers["receiver_agent_identifier"] = request_scoped_urn
    else:
        identifiers["receiver_id"] = None
        identifiers["receiver_agent_id"] = None
        identifiers["receiver_agent_identifier"] = None

    # 4. Parcel ID (sparse)
    if include_parcel:
        identifiers["parcel_id"] = f"p-{uuid_factory()}"
    else:
        identifiers["parcel_id"] = None

    # 5. Pickup Place ID and URN (sparse)
    if include_pickup:
        pickup_uuid = uuid_factory()
        identifiers["pickup_place_id"] = f"pl-{pickup_uuid}"
        identifiers["pickup_place_identifier"] = f"urn:uuid:{pickup_uuid}"
    else:
        identifiers["pickup_place_id"] = None
        identifiers["pickup_place_identifier"] = None

    # 6. Drop-off Place ID and URN (sparse)
    if include_drop_off:
        drop_off_uuid = uuid_factory()
        identifiers["drop_off_place_id"] = f"pl-{drop_off_uuid}"
        identifiers["drop_off_place_identifier"] = f"urn:uuid:{drop_off_uuid}"
    else:
        identifiers["drop_off_place_id"] = None
        identifiers["drop_off_place_identifier"] = None

    return GraphIdentifiers(**identifiers)
