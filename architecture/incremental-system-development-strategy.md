---
title: "Hulubul Incremental System Development Strategy"
version: "v0.5"
date: "2026-07-20"
project: "Hulubul V1"
status: "Baseline for Phase 1 implementation planning"
---

# Hulubul Incremental System Development Strategy

> **Document status:** Finalized as the planning baseline for the current four-phase split. It remains a living strategy: later revisions may refine phase boundaries when implementation evidence justifies a change, but implementation planning should treat the present phase goals, limitations, and architectural commitments as authoritative.

Design intent: preserve a clear path from a minimal end-to-end prototype to the target agentic service without prematurely implementing every production concern.

## 1. Executive summary

Hulubul should be developed as a sequence of complete system increments rather than as one large implementation of UC-1 and UC-3 through UC-9. Each phase must produce a demonstrable end-to-end flow and preserve a deliberate path to the target architecture.

The first phase is a walking skeleton. It includes a skeletal but real implementation of UC-1, persists the request and lifecycle state in Neo4j, uses LangFlow built-in conversation memory, invokes a dedicated Data Access Agent through a LangFlow subflow tool, and completes a simplified parcel lifecycle through simulated communication.

The phase split prioritizes architecture and learning risks: resumability, state ownership, agent-to-agent/tool contracts, structured outputs, Neo4j MCP access, and testability. Matching sophistication, external channels, isolation, recovery, deterministic authorization, and production hardening are added only when they become necessary.

## 2. Phase summary

| **Phase** | **Memorable name** | **Primary result**                                                                                                                                         |
|-----------|--------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1         | Walking Skeleton   | A real request is registered, persisted, assigned to a seeded transporter, accepted, picked up, delivered, and closed through LangFlow chat.               |
| 2         | Working Brokerage  | The combined coordinator is split into specialists; choice, rejection, clarification, fallback, and an LLM guardrail are introduced.                       |
| 3         | Field Pilot        | A real channel, identity mapping, multiple sessions/requests, recovery, basic reliability, and pilot-grade observability are introduced.                   |
| 4         | Hardened Service   | The target use cases are completed with deterministic controls, robust failure handling, stronger matching, isolation, privacy, and production operations. |

## 3. Stable architectural commitments

### 3.1 Business state and conversation history are different

| **Concern**                     | **Phase 1 owner**      | **Meaning**                                                                                |
|---------------------------------|------------------------|--------------------------------------------------------------------------------------------|
| Conversation messages           | LangFlow PostgreSQL    | LangFlow stores and retrieves chat messages under a custom session_id.                     |
| Business process state          | Neo4j                  | DeliveryRequest, RequestStatus, participants, parcel and locations remain authoritative.   |
| Conversation-to-request binding | Neo4j operational node | A lightweight ConversationBinding maps LangFlow session_id to the active DeliveryRequest.  |
| Language interpretation         | Agent memory           | Previous messages help interpret free text, but do not define the request lifecycle stage. |

The picture is therefore: LangFlow manages the session identifier and associated messages in PostgreSQL; Neo4j stores the domain request; ConversationBinding glues them together. For Phase 1, storing the binding in Neo4j is preferable because the routing context can be loaded with the request status in one data-access operation and no custom PostgreSQL schema or repository is needed.

This is a pragmatic operational extension, not a claim that session metadata belongs to the conceptual domain model. The binding should use a clearly separate label or namespace. It should be reconsidered when multiple active requests per conversation, cross-channel identity, or stronger operational-state requirements appear.

### 3.2 Routing is grounded in domain state

Chat Input
→ Data Access flow: getRequestRoutingContext(session_id)
→ Router Agent receives authoritative request status
→ Router selects Request Intake or Parcel Coordination
→ selected specialist performs the interaction

Chat memory may help interpret phrases such as "yes" or "tomorrow morning", but the request status and closed timestamp loaded from Neo4j determine the workflow stage. The routing-context lookup is mandatory preprocessing rather than an optional Router tool.

### 3.3 Data access remains behind one agent boundary

Domain agent
→ Run Flow tool: executeDeliveryDataOperation
→ Data Access Agent
→ Neo4j MCP tool
→ Neo4j
→ structured DataOperationResult

The domain agents decide which logical business operation is needed. The Data Access Agent decides how to read or write the graph through Neo4j MCP. Domain agents never receive the raw MCP tools.

### 3.4 Guardrails evolve without changing callers

| **Phase** | **Write path**                                                                                           |
|-----------|----------------------------------------------------------------------------------------------------------|
| 1         | Domain Agent → Data Access Agent → Neo4j MCP. No guardrail agent; use the configured non-production development Neo4j instance. Testcontainers is reserved for automated tests. |
| 2         | Data Access planning → mandatory LLM Guardrail Agent → conditional MCP execution.                    |
| 4         | Typed operation-specific tools and deterministic authorization/query controls replace the LLM guardrail. |

The external contract remains DataOperationRequest → DataOperationResult, so the internal guardrail stage can be inserted later without redesigning all specialist agents.

### 3.5 Structured outputs and testing start in Phase 1

- Every Agent component uses a defined Structured Response schema.

- The structured result is deterministically rendered to Chat Output so it is visible and stored in LangFlow message history.

- Operational schemas are separate from the conceptual Hulubul domain schema.

- Phase 1 includes automated schema, routing, transition, data-access, integration, end-to-end, and one LLM-as-judge evaluation.

- LangFlow native traces are used for debugging in Phase 1; external OpenTelemetry/OpenInference observability is deferred.

## 4. Phase 1 - Walking Skeleton

### 4.1 What is new

- Skeletal UC-1: create a DeliveryRequest, capture the required minimum data, ask for missing information, and reach complete.

- Router Agent grounded by a mandatory Neo4j routing-context lookup.

- Request Intake Agent and a combined Parcel Coordination Agent.

- Dedicated Data Access Agent invoked as a LangFlow Run Flow tool.

- Neo4j MCP access with `get-schema`, `read-cypher`, and `write-cypher` against the configured non-production development Neo4j instance.

- LangFlow built-in memory and PostgreSQL-backed message history using a custom session_id.

- ConversationBinding in Neo4j for one active request per session.

- Structured outputs and deterministic chat rendering.

- Seeded transporter assignment and simulated outbound communication.

- Rudimentary automated testing and one LLM-as-judge evaluation.

### 4.2 Tool implementation strategy

| **Capability**             | **Phase 1 treatment**                    | **Implementation**                                                                      |
|----------------------------|------------------------------------------|-----------------------------------------------------------------------------------------|
| Create/read/update request | Real                                     | Logical operation → Data Access Agent → Neo4j MCP → Neo4j.                        |
| Resolve routing context    | Real                                     | Read ConversationBinding and DeliveryRequest status from Neo4j before routing.          |
| Completeness check         | Simplified                               | Small required-field profile aligned with the Phase 1 domain subset.                    |
| Transporter selection      | Simplified                               | Assign a configured seeded transporter; no matching or availability calculation.        |
| Forward request            | Simulated                                | Return a CommunicationStub, render it in LangFlow chat, and advance to waitingResponse. |
| Acceptance/pickup/delivery | Simulated actor input + real persistence | Playground/API messages simulate actors; status updates are real Neo4j writes.          |
| Guardrail                  | Deferred                                 | No LLM guardrail in Phase 1. Keep schemas and the data-access boundary.                 |
| Timeout/recovery           | Deferred                                 | No scheduler, reminder, timeout, or automatic fallback.                                 |

### 4.3 Limitations and assumptions

- One active DeliveryRequest per LangFlow session.

- Identity and actor role are trusted or explicitly simulated.

- No production authorization or session isolation.

- No Telegram, WhatsApp, delivery callback, or real outbound send.

- One seeded transporter; no sender choice and no route matching.

- Primary scenario assumes transporter acceptance.

- No rejection, transporter clarification, cancellation, timeout, recovery, attachments, or feedback.

- Closure is represented by delivered plus DeliveryRequest.closed, because the provided RequestStatus enum has no closed value.

- Generic LLM-generated write Cypher is confined to the configured non-production development Neo4j instance, with restricted credentials where practical. Disposable Neo4j instances are used only by automated tests.

### 4.4 Exit criteria

1. A sender message creates the required Phase 1 domain-model subset and a ConversationBinding.

2. An incomplete request produces a clarification question and later resumes the same request.

3. The request reaches complete and a seeded transporter is assigned.

4. A simulated transporter message appears both in chat and as structured output.

5. Acceptance, pickup planning, pickup confirmation, delivery, and closure are persisted.

6. The flow resumes after a LangFlow restart when PostgreSQL and Neo4j are retained.

7. All agent outputs conform to their operational schemas.

8. Automated tests verify valid and invalid transitions and graph changes.

9. One calibrated LLM-as-judge case demonstrates qualitative evaluation.

10. Traces show that only the Data Access Agent invokes Neo4j MCP.

## 5. Phase 2 - Working Brokerage

### 5.1 What is new compared with Walking Skeleton

- Split Parcel Coordination into Matching and Choice, Brokerage, Fulfilment, and optionally Closure agents.

- Add a dedicated Clarification Agent.

- Return up to three simple candidates and let the sender select or rank them.

- Support rejection, next-candidate fallback, and transporter clarification.

- Introduce a mandatory LLM Guardrail Agent between data-access planning and write execution.

- Introduce expected-status checks, idempotency identifiers, and an operational transition log.

- Support multiple requests by adding structured session/request binding rules.

- Add basic actor-operation policy, while identity remains trusted in the test environment.

### 5.2 Limitations

- Matching remains fixed-order or randomized over controlled seeded candidates.

- No real external channel is required.

- The guardrail is probabilistic and not a security boundary.

- Timeouts and compensation remain manual or limited.

## 6. Phase 3 - Field Pilot

### 6.1 What is new compared with Working Brokerage

- Integrate Telegram or another real communication gateway.

- Map Channel.systemID to an Agent and generate trusted session/actor context.

- Support separate sender and transporter conversations and multiple concurrent requests.

- Introduce deterministic reply/request correlation and session isolation.

- Add reminder and timeout scheduling, Recovery Agent, late-response policy, and candidate cascade.

- Add outbound reliability, basic retries, and an outbox or equivalent delivery record.

- Introduce route-based eligibility, pilot-grade observability, and an Admin exception path.

- Add attachment handling only if required by pilot use cases.

### 6.2 Limitations

- Some mutation policy can remain LLM-assisted.

- Matching weights can remain basic.

- The system is pilot-grade rather than generally available.

## 7. Phase 4 - Hardened Service

### 7.1 What is new compared with Field Pilot

- Complete selected and deferred use cases, including preferences, profile/route lifecycle, cancellation, and feedback.

- Replace generic write-cypher with operation-specific mutation tools wherever practical.

- Implement deterministic authorization, state-transition policy, data scope enforcement, and idempotency.

- Add robust failure compensation, privacy/retention controls, complete audit history, and production-grade isolation.

- Strengthen matching, entity resolution, observability, resilience, and scaling.

## 8. Design-document roadmap

| **Prepare now**                                     | **Prepare later**                                                  |
|-----------------------------------------------------|--------------------------------------------------------------------|
| Incremental System Development Strategy             | Detailed Guardrail Agent policy - Phase 2                          |
| Phase 1 Walking Skeleton Blueprint                  | Matching and candidate-cascade specification - Phase 2/3           |
| Verification, Testing, and Evaluation Strategy      | Telegram/channel and identity architecture - Phase 3               |
| Phase 1 operational schemas                         | Timeout, recovery, outbox, and compensation design - Phase 3       |
| Phase 1 domain-model mapping and transition profile | Deterministic authorization and operation-specific tools - Phase 4 |
| Architecture decision and assumptions registers     | Full privacy, retention, scaling, and resilience design - Phase 4  |

## 9. Phase-by-phase decision principle

Only decisions required to implement the next phase should block delivery. The target architecture and deferred constraints should remain visible, but detailed policies should be designed immediately before the phase that needs them.

Phase 1 maximizes architectural learning: real LangFlow orchestration, real schemas, real Neo4j persistence, real resumability, real tests - and intentionally simplified business behavior.

## 10. Source inputs

- Hulubul V1 - Use Cases (DRAFT), supplied by the project owner.

- hulubul.schema.json, supplied domain JSON Schema.

## References

- [LangFlow agents and built-in session memory](https://docs.langflow.org/agents)

- [LangFlow session IDs](https://docs.langflow.org/session-id)

- [LangFlow PostgreSQL application database](https://docs.langflow.org/configuration-custom-database)

- [LangFlow Run Flow component](https://docs.langflow.org/run-flow)

- [LangFlow tools for agents](https://docs.langflow.org/agents-tools)

- [LangFlow MCP Tools component](https://docs.langflow.org/mcp-tools)

- [LangFlow native traces](https://docs.langflow.org/traces)

- [Neo4j MCP tools](https://neo4j.com/docs/mcp/current/tools/)
