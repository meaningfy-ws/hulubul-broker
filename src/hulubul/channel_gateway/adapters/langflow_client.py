import logging

import httpx
from pydantic import ValidationError

from hulubul.channel_gateway.models.channel import ChannelRef
from hulubul.channel_gateway.models.langflow import (
    LangflowRunReply,
    LangflowRunRequest,
    LangflowTweaks,
)

logger = logging.getLogger(__name__)


class LangflowClient:
    def __init__(self, base_url: str, flow_id: str, client: httpx.AsyncClient) -> None:
        self._base_url = base_url.rstrip("/")
        self._flow_id = flow_id
        self._client = client

    async def run(self, session_id: str, channel: ChannelRef, text: str) -> str | None:
        url = f"{self._base_url}/api/v1/run/{self._flow_id}"
        request = LangflowRunRequest(
            input_value=text,
            session_id=session_id,
            tweaks=LangflowTweaks(channel_identity=channel),
        )
        try:
            response = await self._client.post(
                url, json=request.model_dump(mode="json"), timeout=30
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("LangFlow Run API call failed: %s", exc)
            return None

        try:
            return LangflowRunReply.model_validate(response.json()).text
        except (ValidationError, ValueError) as exc:
            logger.warning("Unexpected LangFlow response shape: %s", exc)
            return None
