"""Graph identifier generation service for deterministic UUID management.

Provides stable, deterministic graph node ID generation for:
- Session IDs (random UUID4 for each call)
- Request IDs (deterministic UUID5 based on parcel_intent and receiver_id)
- Delivery IDs (deterministic UUID5 based on request_id and transporter_id)

All outputs are strings in RFC 4122 UUID format.
"""

from uuid import NAMESPACE_DNS, uuid4, uuid5


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
    # Combine inputs into a single seed string for UUID5
    # Prefix with "request:" to distinguish from delivery IDs
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
    # Combine inputs into a single seed string for UUID5
    # Prefix with "delivery:" to distinguish from request IDs
    seed = f"delivery:{request_id}:{transporter_id}"
    return str(uuid5(NAMESPACE_DNS, seed))
