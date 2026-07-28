from typing import Literal

from pydantic import AliasPath, BaseModel, Field

from hulubul.channel_gateway.models.channel import ChannelRef


class LangflowTweaks(BaseModel):
    channel_identity: ChannelRef


class LangflowRunRequest(BaseModel):
    """The LangFlow Run API request contract (`POST /api/v1/run/{flow_id}`)."""

    input_value: str
    session_id: str
    tweaks: LangflowTweaks
    input_type: Literal["chat"] = "chat"
    output_type: Literal["chat"] = "chat"


class LangflowRunReply(BaseModel):
    """The single field this gateway consumes from LangFlow's Run API response."""

    text: str = Field(
        validation_alias=AliasPath("outputs", 0, "outputs", 0, "results", "message", "data", "text")
    )
