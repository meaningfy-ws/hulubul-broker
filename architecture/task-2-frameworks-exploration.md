# Task #2 — Frameworks & Technical Choices: Exploration Brief (DRAFT — complete, non-decisional)

**Purpose:** exploratory, not decisional. Map the problem space and the realistic
options per stack layer, with capabilities, fit to our ADRs, and how the pieces
combine. Decisions come later, in stages.

**Anchoring commitments (from `decisions/`):** Telegram dev / WhatsApp prod
(ADR-003/008) · Neo4j Community as system of record via MCP (ADR-005/015) ·
autonomous agent brokerage (ADR-004) · low-code/UI-first, minimal Meaningfy-compliant
Python core (ADR-016) · deterministic matching + guarded writes outside the LLM
(ADR-012/017) · dialogue-act layer + goal-stack (ADR-014/018) · scheduled recovery
(ADR-010).

---

## 0. The problem space (framing)

Stripped to essentials, Hulubul is a **matching + notification engine with a
slot-filling chat front-end over a graph**. The conversational reasoning is *thin*
(collect fields, validate, confirm — ADR-018 scoped to slot-filling); the weight is
in **proactive/scheduled messaging** and a **deterministic matching + guarded-write
core**. Seven forces decide the stack:

1. **Proactive-messaging economics** — the dominant workload is *outbound* (match
   alerts, pickup/delivery notices, broadcasts). On WhatsApp these are **paid, opt-in,
   templated**; on Telegram free. → favours a strong **scheduler/trigger** layer.
2. **EU data sovereignty** (Meaningfy) — self-hostable, EU-resident, permissive
   licence. → rules out US-cloud-only tools; favours MIT/Apache + self-host.
3. **Low-code/UI-first vs clean-code** (ADR-016) — "as much UI config as possible"
   pulls toward Dify/n8n; "coded parts are cosmic-python + testable" pulls toward
   Python frameworks. **This is the core fork.**
4. **Deterministic core outside the LLM** (ADR-012/017) — matching + writes are
   tested Python, never LLM-authored. → favours explicit-graph orchestration + a
   FastAPI/service core.
5. **Per-party scoping on Neo4j Community** (ADR-015) — no in-engine RBAC → a thin
   **custom scoped MCP/tool server** over services; the stock Cypher MCP is admin-only.
6. **Thin dialogue** (ADR-018, scoped down) — slot-filling only; no need for a
   heavyweight dialogue framework (Rasa) or planner.
7. **We operate it as a product** — licence terms that forbid embedding/reselling
   (n8n SUL, Dify) matter for the long term, even if fine for an internal service now.

The recurring theme: **bet the stack on the scheduler + deterministic core (the hard
parts), not on the chat layer (the easy part).**

## 1. Channel layer — Telegram (dev) + WhatsApp (prod)

**Telegram (dev):** use the **Bot API**, not raw MTProto.

| Lib | License | 2026 status | Note |
|---|---|---|---|
| **aiogram 3.x** | MIT | very active, async-only | **Recommended** — MIT, asyncio fit |
| python-telegram-bot 21 | LGPL-3.0 | active | safe fallback, batteries-included |
| Telethon | MIT | maintenance mode | MTProto client, overkill |
| Pyrogram | LGPL | **unmaintained** | avoid |

**WhatsApp (prod):** EU sovereignty favours an **EU-hosted BSP with a DPA** over Meta-direct.

| Route | Model | EU residency | Verdict |
|---|---|---|---|
| **360dialog** (Berlin BSP) | flat fee + Meta at-cost | EU by default, DPA | **Recommended MVP** — raw API, cheapest at volume |
| respond.io | platform fee + Meta | EU selectable, ISO 27001 | if enterprise SLA needed |
| Meta Cloud API direct | per-msg pass-through | ⚠ weak EU guarantees | you become your own BSP; more plumbing |
| Twilio | Meta + surcharge | EU controls available | best docs, priciest |
| WAHA (self-host, unofficial) | free | full control | **disqualified** — ToS violation, ban risk; Jan-2026 terms bar 3rd-party AI chatbots ⚠ |

**WhatsApp economics (the spine, ⚠ rates shift ~quarterly):** Meta bills **per delivered template**. **Reactive** replies inside the user-opened **24h service window are free**; **proactive** business-initiated messages (match alerts, pickup/delivery notices, broadcasts) are **paid, pre-approved, opt-in-gated templates** — priced by category (utility/auth ~80–90% cheaper than marketing) × country. **Telegram has none of this** (free, unrestricted) — so dev flows must **not** assume that freedom or they break on the WhatsApp swap. Design: react inside the free window where possible; reserve utility templates for genuine proactive pings.

**Abstraction:** one **`ChannelPort`** (services depend on it; providers are adapters). Model outbound as capability-typed value objects — `TextMessage`, `MediaMessage`, `ChoicePrompt(options≤3)`, `InboundMessage` — never raw provider dicts (no-free-strings rule). Keep **template/opt-in/window accounting inside the WhatsApp adapter**; domain just says "notify sender." Expose **capability flags** so services degrade gracefully (>3 options → numbered text list on WhatsApp). Prior art: Vercel Chat SDK uses exactly this per-platform-adapter pattern; its hardest WhatsApp problem is template/business-initiated support — confirming where the friction lives.

**Shortlist:** dev → **aiogram 3.x** on Bot API (webhook); prod → **360dialog** behind a `ChannelPort` adapter; never WAHA in prod; budget proactive notifications as paid utility templates.

## 2. Orchestration / conversation platform

This layer = **NL turns, routing, prompt-tuning UI, glue**. Deterministic matching + guarded Neo4j writes live *outside* it (ADR-012/017).

| Tool | Lang | License | Self-host/EU | Non-dev UI | MCP (client/server) | Native cron+triggers | Testability |
|---|---|---|---|---|---|---|---|
| **Langflow** | Python | MIT | ✅ | ✅ mature | ✅/✅ | ❌ **no native cron** | flow versioning; no unit-runner |
| **Dify** | Python | Apache-2.0 +conditions (no multi-tenant SaaS) | ✅ | ✅ polished | ✅/✅ | ✅ **cron+webhook GA v1.10** | node test + YAML export |
| **n8n** | Node | ⚠ fair-code (no embed/resell) | ✅ | ✅ best automation UX | ✅/✅ | ✅ **best-in-class + native Telegram/WhatsApp nodes** | git source-control (Ent.) |
| **LangGraph** | Python | MIT (Platform paid) | ✅ lib (cron=paid) | ⚠ dev-leaning Studio | ✅/✅ | cron only in paid Platform | ✅✅ checkpoint replay |
| **Pydantic AI** | Python | MIT | ✅ | ❌ code-only | ✅/✅ | none built-in, **but +DBOS = in-lib scheduling+durability** | ✅✅ TestModel/Evals |
| **CrewAI** | Python | MIT (Studio paid) | ✅ | ⚠ paid Studio | ✅/Ent. | none OSS | weak |
| **AG2** (AutoGen fork) | Python | Apache-2.0 | ✅ | ⚠ uncertain | ✅/❌ | none | moderate; **LLM-routing = worst fit for determinism** |
| **Rasa Pro** | Python | source-available, paid (~$35k/yr) | ✅ on-prem | ✅ Studio (paid) | ✅ client (beta) | ✅ `trigger_intent` proactive | ✅ e2e |
| Flowise | Node | open-core | ✅ | ✅ | ⚠ weak client-only | ⚠ | **excluded** — weak MCP + **RCE CVE-2026-40933** |
| Semantic Kernel | .NET/Py | MIT | ✅ | ❌ | ✅/✅ | ❌ | **excluded** — maintenance mode → MS Agent Framework 1.0 |

**Control planes** (bolt onto a code-defined agent to give non-devs prompt/version/eval control without touching the graph): **Langfuse** (MIT, EU, native prompt-mgmt MCP) is the best all-round; **Agenta** (MIT) strong #2.

**Key findings:**
- **MCP-native is broadly solved** — not a differentiator except to **exclude Flowise** (weak + CVE).
- **Scheduling splits the field, and it's our dominant workload.** Native cron+triggers: **n8n (best, + native Telegram/WhatsApp), Dify**. **Langflow has no native cron.** Every Python framework needs external cron **except Pydantic AI+DBOS** (in-library, self-hostable).
- **"Determinism outside the LLM" favours explicit-graph tools** (LangGraph, pydantic-graph, Dify/n8n condition nodes). AG2's LLM-driven speaker selection is the worst fit.
- **The central tension:** polished self-host **low-code** (Dify/Langflow/n8n) vs the tools that best satisfy **clean-architecture + testability + MIT** (Pydantic AI, LangGraph) which are **code-only/dev-leaning**. A code-defined Python agent + **self-hosted Langfuse** is the 2026 way to give non-devs tuning power *without* a visual flow builder.
- **License reality** (we operate this as a product): n8n SUL (no embed/resell), Dify (no multi-tenant SaaS), Rasa Pro paid/source-available. **MIT-clean:** Langflow, LangGraph lib, Pydantic AI, CrewAI lib.
- **Avoid starting on** Semantic Kernel / plain AutoGen (maintenance mode); dead tools (Humanloop shut down, Helicone maintenance).

## 3. Dialogue management (scoped down to slot-filling)

**Decision (user, this session):** the EVA referent is the BDI / plan-based dialogue
system in [Springer 10.1007/s10458-025-09717-5](https://link.springer.com/article/10.1007/s10458-025-09717-5)
— **too heavy for now.** For a transactional flow that reads/writes a knowledge
graph, the MVP dialogue layer is **simple model-driven slot-filling**: enough to
enforce the **mandatory-field validation** rules. **No BDI, no logical formalisms,
no planner, no QUD semantics.**

**What that means concretely:**
- Each goal (send a parcel, register a profile, choose a transporter, confirm) is a
  **form = a domain model with required/optional slots**. "Complete" = all mandatory
  slots present + valid → ties straight into the **Completeness Checker** component
  and ADR-017 boundary validation.
- The **LLM does perception + generation only**: extract slot values from a chat
  message, and phrase the next question/confirmation. The **form + validation logic
  is deterministic, model-driven Python** (unit-testable, no drift).
- **Session/goal-stack (ADR-014) stays** but stays *simple*: a stack of active forms
  so we know "which form are we filling now" when goals interleave in one chat — not
  a QUD/belief engine.

**Tooling note:** Rasa **Forms** is the canonical slot-filling pattern, but a small
model-driven form in our own Python is enough and cleaner for cosmic-python; no need
for Rasa, off-the-shelf DA taggers, or ISO/DAMSL machinery. **ISO 24617-2 is kept
only as an optional naming vocabulary** for intents/acts if it ever helps — not as a
mechanism. Research on the fuller ISU/BDI path is archived for post-MVP if flows
ever get combinatorially complex (graduate the *selection* layer behind the same
service interface — no model/adapter rewrite).

## 4. Neo4j access, MCP & scoping

**MCP servers:** the mature one is Labs **`mcp-neo4j-cypher`** (Python; STDIO/HTTP; `read_neo4j_cypher` in a read-txn + `write_neo4j_cypher`, disableable via `NEO4J_READ_ONLY`; `get_neo4j_schema` needs **APOC**, which runs on Community). Official `neo4j/mcp` binary is newer/Aura-oriented — read-only story less proven (⚠ verify per release). Both are **Labs/beta grade — pin versions.**

**The crux:** a read-only Cypher MCP is still **all-or-nothing** — it exposes the *whole* graph, and Community has **no in-engine row/label security** (§ below). So per-party isolation **must** live in-app.

**Recommended access architecture (maps to ADR-015):**
- **Party-facing agents → a thin, custom MCP/tool server exposing only named, per-party-scoped operations** (e.g. `orders_for_party`, `public_profile_of_contact`) over the cosmic-python service layer. Cypher is developer-authored inside each operation; **party id is bound from the authenticated session server-side, never from the LLM.** No generic Cypher tool in the party path.
- **Admin agent → the generic Labs `mcp-neo4j-cypher`** on a *separate, audited* credential (read-only toggled per need). Elevation is a distinct logged surface.
- This is the graph analogue of Postgres RLS, done in-app because Community can't. ⚠ **Note: this refines ADR-005** ("all access via *the* Neo4j MCP") — party path is a *custom scoped* MCP, not the stock one.

**Community limits (2026, confirmed):** no RBAC / sub-graph (label/property) security, **single database** (no db-per-tenant), no LDAP/CDC/clustering. → **100% of tenant isolation is app-layer; one scoping bug = cross-party leak** (document as a security assumption). Native `point`+spatial index, native vector index, APOC Core **are** on Community.

**Drivers:** official **`neo4j` driver** in `adapters/` for the write/service layer (explicit txns, unit-of-work). **neomodel** (Labs, official py2neo successor) optional, confined to `adapters/`. **py2neo is EOL — avoid.**

**Geospatial:** Neo4j Community **sufficient for MVP** — native `point`, spatial index, `point.distance()` (radius) and `withinBBox()`; "route passes through zone within N hours" is a graph+temporal query (Neo4j's sweet spot). Polygon-in-point is hand-rolled (bbox prefilter + fine test). **Offload to PostGIS only if polygon complexity grows.**

**Vector DB:** **defer Qdrant.** Neo4j native vector index (on Community) is enough for light MVP semantic matching (~5× slower than Qdrant, post-filter only — fine at MVP scale). Keep semantic matching behind an interface (DIP) so Qdrant+Neo4j GraphRAG is a later adapter swap.

## 5. Workflow / scheduling + LLM gateway

**Two distinct jobs:** (a) event fan-out (new order → find transporters → notify) and (b) timed recovery (nudge unread ~1–2h, status ~24h, max 3 → close).

| Engine | Lang | License | Durable/resumable | Fit |
|---|---|---|---|---|
| **cron + APScheduler** | Python | MIT | state in Neo4j, not engine | **MVP pick** — deterministic sweep in `services/`, lowest ops |
| n8n | Node | ⚠ fair-code (self-host/internal OK; no reselling as SaaS) | partial | thin UI trigger/dispatch layer only; keep logic in Python |
| Prefect 3 | Python | Apache-2.0 core | retries, light durability | middle ground; more infra than needed for MVP |
| Airflow | Python | Apache-2.0 | batch DAGs, not event/conversation | overkill/wrong shape |
| Dagster | Python | Apache-2.0 | asset pipelines | wrong shape |
| Temporal | Py SDK | MIT (⚠ verify) | ✅✅ gold-standard durable execution | ideal but **heavy for MVP** (needs Cassandra/Postgres+K8s); revisit post-MVP |

**Durable-vs-cron verdict:** **cron/APScheduler + Neo4j-persisted state for MVP.** Recovery is a simple, idempotent state machine (`next_action_at`, `nudge_count`, terminal close); a periodic sweep + **compare-and-set Cypher write** gives "advance-once" without a durable engine. Keep the recovery *decision* a pure unit-testable `services` function; the scheduler is just an `entrypoint` → the durable-vs-cron choice stays reversible (DIP). Adopt Temporal/Prefect later only if recovery flows multiply (saga/compensation, per-conversation timers).

**Scheduling state:** lives in **Neo4j** (system of record); scheduler stays **stateless** (each tick queries due conversations, advances, writes back). Avoid a second authoritative timing store (APScheduler jobstore / n8n execution store).

**LLM gateway:** **LiteLLM, self-hosted in EU** — MIT, OpenAI-compatible, native Anthropic, budgets/fallbacks; only the model call leaves the box, swapping to a local/EU model is config-only. (OpenRouter ruled out — no self-host; Portkey the alt if you want built-in guardrails/PII/audit, Apache-2.0 core ⚠ confirm OSS scope.)

**Two-tier NL strategy behind the gateway** (model ID = config read by an `adapter`, never hard-coded): **Haiku 4.5** (`claude-haiku-4-5`, ~$1/$5) for intent classification/field extraction/routing; **Sonnet 4.6** for higher-volume NL; **Opus 4.8** for multi-step planning. Two independent swap axes: provider and tier.

## 6. Testing & observability

**Spine:** **pytest + pytest-bdd** (house tools) for the Python core & BDD; **DeepEval** (Apache-2.0, pytest-native) for LLM/agent behaviour assertions; **Langfuse** (MIT, self-host, EU region, OTel-native) for tracing across both low-code flows and Python core.

| Tool | Purpose | Self-host/EU | License | Note |
|---|---|---|---|---|
| **DeepEval** | agent/conversation behaviour eval | yes | Apache-2.0 | pytest-native, multi-turn + tool-use metrics; **pick** |
| **Langfuse** | tracing + eval | yes, EU | MIT core | OTel-first, one trace across both worlds; **pick** |
| Giskard-OSS | red-team/safety scan | yes | Apache-2.0 | optional, post-MVP |
| promptfoo | eval/red-team | yes | MIT | ⚠ OpenAI-acquired 2026-03 — neutrality risk |
| LangSmith | obs+eval | self-host Enterprise-only, US | proprietary | weak EU story — skip as primary |
| Ragas | RAG metrics | yes | Apache-2.0 | only if retrieval appears |

**Testing low-code workflows — realistic pattern:** **black-box HTTP from pytest** — POST an inbound payload to the flow's webhook/API, assert the outbound message + graph side-effects. Real and practical, but **the ceiling**: no unit isolation inside a flow, can't mock inside a node (the flow must call *your* stubbable Python service, not embed I/O — which is the clean-architecture-correct move anyway), noisy JSON/YAML diffs, non-determinism needs judge/threshold assertions. Langflow has the best flow-as-code story (`lfx validate` in CI); Dify DSL import is UI-only ⚠.

**BDD wiring:** Gherkin `Scenario Outline` → step defs drive a **faked channel** (in-memory message queue) + **faked Neo4j** (`FakeGraphRepository` port, or a throwaway testcontainer for integration); `Given` seeds graph, `When` injects turns, `Then` asserts **both** dialogue outcome **and** graph state (guarded-write + scoping invariants). Run **two profiles**: fast deterministic (LLM mocked) gates every commit; slow live-agent (real model + DeepEval) runs nightly.

**Pragmatic MVP pyramid:** rigorous on the deterministic core (models, **matching + guarded writes** via pytest + **Hypothesis** property tests, services with faked adapters); focused on DA/slot routing (unit-test the deterministic table + a small threshold-gated classifier eval); smoke + threshold-gated on agent behaviour (nightly, not per-commit); selective BDD golden paths; **smoke-only** on low-code flows; instrument OTel/Langfuse but **don't gate** on it at MVP. **YAGNI cuts:** red-teaming, paid eval SaaS, Dify round-trip CI, per-commit live-LLM tests.

---

## 7. Candidate stack shapes (synthesis)

All three share a **common spine** (well-supported by the research, low controversy):
Telegram **aiogram** → **`ChannelPort`** adapter → **WhatsApp 360dialog** later ·
**Neo4j Community** system of record · **party-facing = thin custom scoped MCP/tool
server over cosmic-python services**; **admin = stock `mcp-neo4j-cypher` (audited)** ·
deterministic **matching + guarded writes = tested Python (FastAPI service)** ·
**LiteLLM** gateway with Haiku/Sonnet tiers · **cron/APScheduler + Neo4j state** for
recovery · **pytest/pytest-bdd + DeepEval + self-hosted Langfuse** for test/trace.

They differ only in **who orchestrates the NL turns + triggers**:

### Shape A — Single low-code tool (**Dify**)
Dify owns triggers (cron+webhook GA), NL slot-filling turns, routing, and MCP calls;
matching/writes are HTTP/MCP calls out to the FastAPI core.
- **+** Fewest moving parts; non-devs tune everything in one UI; best fit for
  ADR-016's "as much UI as possible"; Python-based; cron built-in.
- **−** Orchestration logic lives in visual nodes (weaker cosmic-python fit + harder
  to unit-test); Dify licence forbids multi-tenant SaaS; Telegram/WhatsApp are
  custom (Dify has no native messaging nodes — unlike n8n).

### Shape B — Split: **n8n + Dify/Langflow + FastAPI core** *(the option floated earlier)*
n8n owns cron/webhooks/**native Telegram+WhatsApp** broadcasts + orchestration; a
chat-flow tool (or n8n's own AI node) handles NL turns; FastAPI core owns matching +
guarded writes as an MCP/HTTP tool.
- **+** Each tool at its strength; n8n unmatched for proactive/scheduled + **free
  messaging connectors**; determinism in tested Python; non-devs still get a flow UI.
- **−** Most moving parts / integration seams; two orchestrators risk overlap; n8n
  is Node (off the Python line) and **fair-code** (no resell); a third system to run.

### Shape C — Python agent + control plane: **Pydantic AI (+DBOS) + Langfuse + FastAPI core**
Code-defined Pydantic AI agent for NL turns + MCP tool-calls; **DBOS** gives
in-library scheduling + durable notifications (no separate scheduler); matching is
ordinary tested Python; **self-hosted EU Langfuse** is the non-dev surface for
prompts/versions/evals.
- **+** Cleanest cosmic-python + testability + type-safety; **MIT/Apache throughout**;
  full EU self-sovereignty; scheduling solved in-library; determinism fully outside
  the LLM; strongest test story.
- **−** **No visual flow builder** — non-devs get prompt/eval control via Langfuse but
  can't re-wire flows (partial tension with ADR-016); more upfront Python; you build
  the channel adapters (which the common spine already assumes anyway).

**How the shapes trade against the forces:** A maximises force #3-low-code and #1 is
adequate; B maximises #1 (messaging+scheduling) and keeps #4 clean but is heaviest and
weakest on #2/#7 licence; C maximises #2/#4/testability but concedes the visual
builder half of #3. Because the conversational surface is thin (force #6) and the hard
parts are the scheduler + deterministic core (#1/#4), **B and C are the serious
contenders; A over-weights the easy chat layer.** No decision now — this is the fork
to weigh with real data (broadcast volume, who actually tunes flows).

## 8. Open decisions to lock in later stages

1. **The orchestration fork (B vs C)** — depends on *who tunes flows* (non-dev flow
   editing → B; prompt/threshold tuning is enough → C) and *how much proactive volume*
   there is. Prototype both thin slices before committing. → later ADR.
2. **`ChannelPort` capability set** — the common-denominator message value objects and
   how WhatsApp templates/opt-in map onto them → **modelling session**.
3. **Scoped-MCP operation catalogue** — the exact named per-party operations and the
   visibility rule ("own pact + public info of prior contacts") → **modelling session**
   (ADR-015 guardrails, documented after the data model).
4. **WhatsApp templates + consent model** — GDPR/opt-in, template categories/costs →
   a new concern to add before the prod cutover (not needed for Telegram dev).
5. **Refinement to ADR-005** — party path uses a *custom scoped* MCP, not the stock
   Neo4j MCP; fold this wording back when consolidating (task #3).
6. **Re-verify before build** — versions/licences move monthly; re-check n8n SUL,
   Dify licence, MCP/cron capabilities, and the official `neo4j/mcp` read-only story
   against primary docs at decision time.

---

*Status: exploration complete; decisional forks deferred by design. Sources are in the
per-layer subagent findings; re-verify version/licence-sensitive claims at commit time.*
