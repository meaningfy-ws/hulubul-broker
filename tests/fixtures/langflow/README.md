# LangFlow test fixtures

`dev_echo_flow.json` is a trivial `ChatInput -> ChatOutput` flow (no LLM, no
tools) that echoes whatever text it receives. It exists purely for local
`channel-gateway` smoke testing — confirming the gateway can reach LangFlow
and get a reply back — and is deliberately kept out of `langflow/flows/`
(the manifest-controlled Change-1 flows) since it isn't part of that
deployment topology.

## Import it into a running LangFlow instance

Requires `LANGFLOW_API_KEY` set in `infra/.env` (see `infra/.env.example`)
and the stack up (`make up`):

```bash
curl -s -X POST "http://127.0.0.1:7860/api/v1/flows/" \
  -H "x-api-key: $LANGFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/langflow/dev_echo_flow.json \
  | jq -r '.id'
```

Copy the printed id into `infra/.env` as `LANGFLOW_FLOW_ID`, then restart the
gateway (`docker compose up -d channel-gateway` from `infra/`). Each import
creates a new flow (LangFlow assigns a fresh id) — delete old copies from the
LangFlow UI if you re-import repeatedly.
