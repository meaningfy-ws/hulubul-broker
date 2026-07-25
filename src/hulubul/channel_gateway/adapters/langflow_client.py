import json
import logging
from typing import cast

import httpx

logger = logging.getLogger(__name__)


class LangflowClient:
    def __init__(self, base_url: str, flow_id: str, client: httpx.AsyncClient) -> None:
        self._base_url = base_url.rstrip("/")
        self._flow_id = flow_id
        self._client = client

    async def run(self, session_id: str, medium: str, system_id: str, text: str) -> str | None:
        url = f"{self._base_url}/api/v1/run/{self._flow_id}"
        payload = {
            "input_value": text,
            "output_type": "chat",
            "input_type": "chat",
            "session_id": session_id,
            "tweaks": {
                "channel_identity": {"medium": medium, "system_id": system_id},
            },
        }
        try:
            response = await self._client.post(url, json=payload, timeout=30)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("LangFlow Run API call failed: %s", exc)
            return None

        try:
            data = response.json()
            return cast(str, data["outputs"][0]["outputs"][0]["results"]["message"]["data"]["text"])
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("Unexpected LangFlow response shape: %s", exc)
            return None
