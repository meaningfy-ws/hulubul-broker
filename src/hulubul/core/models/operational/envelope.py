"""Trusted actor context and main flow input envelope."""
from uuid import UUID

from .base import (
    ActorUrn,
    HumanSuppliedText,
    NonBlankText,
    SessionId,
    StrictModel,
    VersionedContract,
)
from .enums import ActorRole, IdentityAssurance, InvocationSource

__all__ = [
    "ActorContext",
    "MainFlowInput",
]


class ActorContext(StrictModel):
    """Trusted actor context (metadata only, no secrets)."""

    actor_id: ActorUrn
    display_name: NonBlankText
    actor_role: ActorRole = ActorRole.SENDER
    identity_assurance: IdentityAssurance = IdentityAssurance.SIMULATED


class MainFlowInput(VersionedContract):
    """Main flow input with trusted envelope and user message."""

    message_id: UUID
    session_id: SessionId
    actor: ActorContext
    source: InvocationSource
    message: HumanSuppliedText
