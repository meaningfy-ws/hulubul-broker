# Chat-driven test copies

Observability harnesses for the canonical flows in `../flows/`. Not deployable
artifacts: they are deliberately **outside** `../flows/` so the flow manifest,
`scripts/validate_langflow_assets.py` and the static topology tests keep
describing exactly the three canonical flows.

## What they are

Each file is its source flow with two nodes added and nothing else changed: a
`ChatInput` feeding the flow's public input component, and a `ChatOutput` fed by
its public result component. The wrapped components' `is_input`/`is_output`
flags are cleared so the chat nodes own the Run API's entry and exit.

Everything a run exercises -- boundaries, agent, prompts, the Run Flow node --
is the same object as in the canonical flow, so what a copy demonstrates holds
for the original. Only the two ends differ.

The point is that runs land in LangFlow's **chat history**, so they can be
opened in the Playground and read turn by turn. The canonical flows are driven
through the Run API against a custom boundary component and leave no chat trace.

| File | Source | Flow id |
|---|---|---|
| `lf-10-request-intake-test.json` | `../flows/20-lf-10-request-intake.json` | `2b0ed901-f1ec-5647-9bda-346514544c27` |
| `lf-70-data-access-test.json` | `../flows/10-lf-70-data-access.json` | `c6d63e07-a3e6-5c5b-b700-47b3e9702654` |

`lf-10-request-intake-test` calls the **canonical** LF-70, not the test copy --
that hop is the thing under test.

## Regenerating

```bash
poetry run python scripts/make_chat_test_flow.py \
    langflow/flows/20-lf-10-request-intake.json \
    HulubulContractInputBoundary-hlb-lf-10-input-v1 \
    HulubulContractResultBoundary-hlb-lf-10-result-v1 \
    langflow/test-flows/lf-10-request-intake-test.json \
    lf-10-request-intake-test
poetry run python scripts/normalize_langflow_flows.py langflow/test-flows/*.json
```

Flow ids are UUIDv5 over the flow name, so regenerating keeps the same id and a
redeploy updates the existing flow rather than creating a duplicate.

## Deploying

`POST /api/v1/flows/` with `{"id", "name", "description", "data"}` to create,
`PATCH /api/v1/flows/{id}` with `{"data"}` to update. Regenerate and redeploy
after any change to the source flow -- these copies do not track it
automatically.

## Driving them

The chat message *is* the flow's public contract, serialized as JSON:

- `lf-10-request-intake-test` takes an `IntakeInput` and answers with an
  `IntakeResult` (or an `OperationalError` when the boundary refuses).
- `lf-70-data-access-test` takes a `DataOperationRequest` and answers with a
  `DataOperationResult`, which LF-70 emits inside a ```json fence.

Use `input_type: "chat"` and `output_type: "chat"`, and one `session_id` per
case so each case is its own readable Playground thread.
