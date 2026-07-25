from dataclasses import dataclass

from hulubul.core.models.domain.hulubul_models import Medium


@dataclass(frozen=True)
class ChannelRef:
    """The (medium, systemID) identity pair — a reference, not the full Channel entity.

    The full `Channel` entity (id, validationStatus, alias, telephone, email) is modeled in
    model/linkml/hulubul_channel.yaml and generated into
    hulubul.core.models.domain.hulubul_models. It is resolved downstream by
    resolve_channel_actor, never constructed here — its `id` is a graph node identity that
    only exists once the node is persisted.
    """

    medium: Medium
    system_id: str


def derive_session_id(medium: Medium, system_id: str) -> str:
    return f"{medium.value}:{system_id}"
