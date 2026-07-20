---
title: "Hulubul Verification, Testing, and Evaluation Strategy"
version: "v0.2"
date: "2026-07-20"
project: "Hulubul V1"
status: "Working design document"
---

# Hulubul Verification, Testing, and Evaluation Strategy

Design intent: preserve a clear path from a minimal end-to-end prototype to the target agentic service without prematurely implementing every production concern.

## 1. Purpose

This document defines how Hulubul flows are verified as the system grows. It treats testing as a cross-cutting development practice: each delivery phase expands both the product behavior and its automated verification suite.

Phase 1 must already be testable. Most correctness checks are deterministic: schema validation, routing, allowed transitions, graph changes, and end-to-end outcomes. One LLM-as-judge evaluation is added to prove the qualitative-evaluation approach without making core workflow correctness depend on a judge model.

## 2. How testing a LangFlow system works

A LangFlow application is a serialized graph of components plus model/tool configuration. Testing therefore happens at several levels rather than through one built-in "unit test" feature.

| **Level**                  | **What it proves**                                              | **How**                                                                                                  |
|----------------------------|-----------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| Playground exploration     | The flow behaves plausibly and calls expected tools.            | Run scenarios manually; inspect tool calls, intermediate results, memory, and chat output.               |
| Flow definition validation | The exported flow JSON is structurally valid.                   | Version flows in Git and run lfx validate.                                                               |
| Contract tests             | Agent and subflow outputs conform to operational schemas.       | Invoke flows through the API and validate JSON Schema/Pydantic models.                                   |
| Integration tests          | Data Access Agent, MCP server, and Neo4j work together.         | Run a test-only disposable Neo4j instance, execute LF-70, and assert graph state directly.               |
| End-to-end tests           | Several chat interactions produce the expected final lifecycle. | Call LF-00 through the LangFlow API with a unique session_id.                                            |
| Evaluations                | Agent decisions and language quality meet defined expectations. | Use exact expected labels for deterministic evals and a narrow LLM-as-judge rubric for one quality case. |
| Trace inspection           | The internal execution path is understandable.                  | Use LangFlow native traces for component/tool spans, errors, latency, and token usage.                   |

## 3. Recommended Phase 1 test stack

| **Tool**                          | **Role**                                                                     |
|-----------------------------------|------------------------------------------------------------------------------|
| pytest                            | Test runner and fixtures for schema, API, integration, and end-to-end tests. |
| Pydantic or jsonschema            | Validate operational results independently of the model and LangFlow UI.     |
| testcontainers-python             | Start a test-only disposable Neo4j database for each test session or suite.  |
| Neo4j Python driver               | Seed data and independently assert resulting graph state.                    |
| LangFlow API client / HTTP client | Invoke LF-00 and LF-70 programmatically.                                     |
| lfx validate                      | Check exported flow JSON before runtime tests.                               |
| LangFlow native traces            | Debug failed flows and verify which component/tool was called.               |
| A separate judge model            | Run one calibrated qualitative evaluation.                                   |

## 4. Testcontainers for Neo4j

> **Scope clarification:** Testcontainers is used only by automated tests. Development and production continue to use the project's configured Neo4j instances.

Yes, a Neo4j-specific Testcontainers implementation exists for Python. Neo4jContainer starts a standalone Neo4j instance and exposes a driver for tests. This is a good fit because LangFlow is Python-based and the test harness can use pytest.

```python
from testcontainers.neo4j import Neo4jContainer

with Neo4jContainer(image="neo4j:5") as neo4j:
    uri = neo4j.get_connection_url()
    # Configure the Neo4j MCP server to use this URI.
    # Invoke the LangFlow Data Access flow.
    # Assert the graph directly with the Neo4j driver.
```

### 4.1 Recommended scope

- Use Testcontainers for the Neo4j database in Data Access integration tests.

- Start the Neo4j MCP server against the Testcontainer. A generic DockerContainer or a test Docker Compose stack can be used if the MCP server is containerized.

- For the first suite, LangFlow itself may run as the normal development container and be invoked through its API.

- Later, a complete disposable stack can include LangFlow, PostgreSQL, Neo4j, and Neo4j MCP.

Tests require a Docker-compatible runtime. In CI, use a runner that supports Docker or an equivalent Testcontainers environment.

## 5. Phase 1 test layers

### 5.1 Flow-definition checks

- Export LF-00, LF-10, LF-20, and LF-70 to version control.

- Run lfx validate for every flow in CI.

- Reject accidental references to missing components, invalid wiring, or undeclared dependencies before runtime tests.

```bash
lfx validate flows/*.json
```

### 5.2 Operational-schema tests

Validate every flow result against a versioned schema. LangFlow structured output encourages the model to return the shape, but the test harness remains the independent validator.

- Required fields are present.

- Enum values are allowed.

- No undeclared fields appear where additionalProperties is false.

- Request and session identifiers are not empty for successful operations.

- CommunicationStub is present only for simulated communication operations.

- A failure result contains a stable error_code and does not claim a successful state change.

### 5.3 Routing tests

| **Routing context**      | **Input**                 | **Expected**                             |
|--------------------------|---------------------------|------------------------------------------|
| No binding               | I want to send a parcel.  | Request Intake                           |
| needsClarification       | The receiver is Ana.      | Request Intake                           |
| waitingResponse          | As transporter, I accept. | Parcel Coordination                      |
| pickUpPlanned            | I collected the parcel.   | Parcel Coordination                      |
| closed timestamp present | Change the pickup time.   | No mutation; informational response      |
| Missing/invalid context  | Yes.                      | Structured failure; no memory-only guess |

### 5.4 Data Access integration tests

1. Start an empty Neo4j Testcontainer.

2. Start/configure Neo4j MCP against that container.

3. Seed the configured transporter through the Neo4j driver.

4. Invoke LF-70 through LangFlow API with a DataOperationRequest.

5. Assert the returned DataOperationResult schema.

6. Query Neo4j directly with the driver and assert nodes, relationships, properties, status, and affected scope.

7. Run a negative operation and confirm the graph did not change.

| **Operation**            | **Key assertion**                                                                               |
|--------------------------|-------------------------------------------------------------------------------------------------|
| createDeliveryRequest    | DeliveryRequest, participants, Parcel, Places, and ConversationBinding exist.                   |
| getRequestRoutingContext | Correct request ID, status, closed flag, and assigned transporter are returned for the session. |
| assignSeededTransporter  | Only the configured transporter participation is attached.                                      |
| setRequestStatus         | Valid expected status updates exactly one request.                                              |
| invalid setRequestStatus | No write occurs; stable error is returned.                                                      |
| setClosedTimestamp       | closed is set only after delivered in the Phase 1 profile.                                      |

### 5.5 End-to-end tests

1. Complete request in one sender message.

2. Incomplete request followed by one clarification response.

3. Full flow through seeded assignment, simulated forwarding, acceptance, pickup, delivery, and closure.

4. Restart LangFlow while keeping PostgreSQL and Neo4j, then resume the same session.

5. Malformed structured result is rejected or mapped to a controlled failure.

6. Invalid lifecycle command does not change the request.

7. Simulated outbound message is available as structured data and is visible in/stored by Chat Output.

### 5.6 Deterministic agent evals

Use a small versioned dataset, initially around 15 to 25 cases. Most evals compare structured fields rather than free-text answers.

| **Evaluated behavior**    | **Deterministic metric**                                                |
|---------------------------|-------------------------------------------------------------------------|
| Routing                   | Exact target_agent match.                                               |
| Required-field extraction | Field-level precision/recall or exact match on normalized fixture data. |
| Missing-field detection   | Exact set match.                                                        |
| Tool/operation selection  | Exact operation enum match.                                             |
| Status transition         | Exact resulting status and graph-state assertion.                       |
| Schema compliance         | Pass/fail JSON Schema or Pydantic validation.                           |

## 6. Required LLM-as-judge experiment

Phase 1 includes one narrow judge case to validate the approach, not to replace deterministic tests.

### 6.1 Recommended case

Judge the quality of the Intake Agent clarification question when several fields are missing.

Input context:
- Known: pickup location and parcel contents
- Missing: receiver and drop-off location

Candidate response:
"Who should receive the parcel, and in which city should it be delivered?"

Judge rubric (0-2 each):
- asks only for genuinely missing information
- is unambiguous
- is concise
- does not invent data
- is suitable for a non-technical user

Pass threshold: total \>= 8/10 and no criterion scored 0.

### 6.2 Execution rules

- Use a separate judge model from the model being evaluated where practical.

- Use temperature 0 or the lowest available value.

- Require a structured JudgeResult with scores, reasons, total, and pass flag.

- Run the case several times during calibration and record variance.

- Initially treat it as informational or a soft gate; promote it to a hard CI gate only after stability is demonstrated.

## 7. Native LangFlow traces versus OpenTelemetry/OpenInference

### 7.1 Phase 1 decision

LangFlow native traces are sufficient for Phase 1 flow debugging. They capture flow runs, component spans, LangChain/tool/LLM spans, inputs, outputs, latency, errors, model metadata, and token usage where available. They are stored in LangFlow trace/span tables and can be inspected in the UI or queried through the monitoring API.

Therefore Phase 1 does not need an OpenTelemetry/OpenInference stack.

### 7.2 What native traces do not fully replace

- Cross-service distributed tracing once Telegram gateway, Neo4j MCP, schedulers, and external services run separately.

- A vendor-neutral export pipeline and correlation with infrastructure metrics and logs.

- Specialized LLM analytics, production dashboards, alerting, long-term retention, and dataset/evaluation workflows.

- End-to-end service-level traces outside the LangFlow runtime.

Reassess in Phase 3. LangFlow provides integrations such as Arize, which is based on OpenTelemetry and OpenInference, as well as Langfuse and Traceloop. Adopt one only when distributed pilot observability creates a concrete need.

## 8. Trace use in tests

- Use traces primarily for diagnosis, not as the sole correctness oracle.

- For selected integration tests, query traces to confirm that the Router called the expected specialist and that only LF-70 invoked MCP.

- Inspect duplicate model calls, especially around Structured Response and Chat Output wiring.

- Record latency and token usage as baselines, but do not set strict Phase 1 performance gates unless regressions become problematic.

## 9. Test data and isolation

- Use unique session_id, request ID, Agent identifier, and correlation ID per test.

- Seed one stable transporter fixture.

- Prefer a fresh Neo4j container per test session; clean or namespace data between tests.

- Use a dedicated LangFlow test project and model configuration.

- Never run tests using production Neo4j credentials or data.

- Record model, prompt, flow, schema, and dataset versions in evaluation results.

## 10. Suggested CI sequence

1. Lint/test Python test code
2. Validate exported LangFlow flows with lfx validate
3. Validate operational JSON Schemas/Pydantic models
4. Start Neo4j Testcontainer (+ MCP test server)
5. Run Data Access integration tests
6. Run Router and specialist flow API tests
7. Run Phase 1 end-to-end scenarios
8. Run deterministic eval dataset
9. Run one LLM-as-judge case (initially soft gate)
10. Upload test reports and selected LangFlow traces

## 11. Phase 1 verification exit criteria

1. All four exported flows pass structural validation.

2. All operational models pass independent schema tests.

3. Each Phase 1 transition has a positive test and at least one invalid-state test.

4. Data Access integration tests run against a test-only disposable Neo4j database.

5. The graph is asserted independently after every write operation.

6. The complete happy path and clarification path pass through the LangFlow API.

7. Restart/resume is demonstrated.

8. The structured communication stub is visible in chat and returned structurally.

9. The LLM-as-judge experiment is calibrated and recorded.

10. Native traces confirm the intended agent/tool boundary.

## 12. Testing additions in later phases

| **Phase**             | **New verification focus**                                                                                                                 |
|-----------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| 2 - Working Brokerage | Guardrail allow/deny dataset, rejection/cascade, transporter clarification, duplicate operations, multi-request routing.                   |
| 3 - Field Pilot       | Gateway contract tests, channel correlation, timeout/recovery, outbox/retries, isolation, distributed trace correlation, load smoke tests. |
| 4 - Hardened Service  | Authorization matrix, deterministic policy property tests, compensation/chaos tests, privacy/retention, security and scale testing.        |

## 13. Concise newcomer workflow

1. Build and inspect the flow in Playground; verify tool calls and structured output.

2. Export the flow JSON and put it in Git.

3. Write an API test that sends input with a unique session_id and validates the structured result.

4. For automated database tests, start a disposable Neo4j instance with Testcontainers and assert the graph with the Neo4j driver.

5. Add the scenario to the deterministic eval dataset when it exercises an agent decision.

6. Use LangFlow traces when a test fails to see the exact component and tool path.

## References

- [LangFlow Playground](https://docs.langflow.org/concepts-playground)

- [LangFlow Flow DevOps Toolkit and lfx validate](https://docs.langflow.org/flow-devops-sdk)

- [LangFlow flow API endpoints](https://docs.langflow.org/api-flows-run)

- [LangFlow agents and structured output behavior](https://docs.langflow.org/agents)

- [LangFlow native traces](https://docs.langflow.org/traces)

- [LangFlow Arize/OpenTelemetry/OpenInference integration](https://docs.langflow.org/integrations-arize)

- [Testcontainers for Python Neo4jContainer](https://testcontainers-python.readthedocs.io/en/latest/modules/neo4j/README.html)

- [Testcontainers runtime requirements](https://java.testcontainers.org/supported_docker_environment/)

- [Neo4j MCP tools](https://neo4j.com/docs/mcp/current/tools/)
