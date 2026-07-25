from dataclasses import dataclass

from hulubul.core.models.domain.hulubul_models import Medium


@dataclass(frozen=True)
class InboundMessage:
    medium: Medium
    system_id: str
    text: str
    reply_to_message_id: str | None = None


@dataclass(frozen=True)
class TextMessage:
    text: str


@dataclass(frozen=True)
class MediaMessage:
    url: str
    caption: str | None = None
