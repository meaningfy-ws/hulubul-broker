SHELL=/bin/bash -o pipefail

BUILD_PRINT = \e[1;34m
END_BUILD_PRINT = \e[0m

REPO_ROOT    := $(shell pwd)
INFRA_PATH   := $(REPO_ROOT)/infra
SCHEMA       := $(REPO_ROOT)/model/linkml/hulubul.yaml
GEN          := $(REPO_ROOT)/model/generated
DIAG         := $(GEN)/diagrams
COMPOSE_FILE := $(INFRA_PATH)/docker-compose.yaml
ENV_FILE     := $(INFRA_PATH)/.env
NEO4J_CY     := $(INFRA_PATH)/cypher
# Neo4j credentials are read from .env (gitignored) so secrets never live in VCS.
NEO4J_USR    := neo4j
NEO4J_PW     := $(shell sed -n 's/^NEO4J_PASSWORD=//p' $(ENV_FILE) 2>/dev/null)
# Run a cypher file into Neo4j via the bundled cypher-shell (no local client needed).
NEO4J_RUN    := docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) exec -T --env NEO4J_USERNAME=$(NEO4J_USR) --env NEO4J_PASSWORD=$(NEO4J_PW) neo4j cypher-shell --format plain

ICON_DONE    = [✔]
ICON_ERROR   = [x]
ICON_WARNING = [!]
ICON_PROGRESS = [-]

#-----------------------------------------------------------------------------
# Deterministic generation from the Hulubul LinkML model.
# Generation runs outside the LLM path — never hand-edit a generated file.
# Requires linkml installed:  pip install linkml  (or: uv pip install linkml)
#-----------------------------------------------------------------------------
.PHONY: help all lint pydantic owl shacl jsonschema erdiagram plantuml classdiagram neo4j neo4j-constraints neomodel clean install ci-static

help: ## Display available targets
	@ echo -e "$(BUILD_PRINT)Available targets:$(END_BUILD_PRINT)"
	@ echo ""
	@ echo -e "  $(BUILD_PRINT)Model generation:$(END_BUILD_PRINT)"
	@ echo "    all                 - Generate every artifact (lint + pydantic + owl + shacl + jsonschema + diagrams + neo4j)"
	@ echo "    lint                - Lint the LinkML schema"
	@ echo "    pydantic            - Generate Pydantic classes"
	@ echo "    owl                 - Generate OWL ontology"
	@ echo "    shacl               - Generate SHACL shapes"
	@ echo "    jsonschema          - Generate JSON Schema"
	@ echo "    erdiagram           - Generate ER diagram (Mermaid)"
	@ echo "    plantuml            - Generate UML class diagram (PlantUML)"
	@ echo "    classdiagram        - Generate whole-model UML class diagram (Mermaid)"
	@ echo "    neo4j               - Show notes on loading Neo4j via linkml-store"
	@ echo "    neo4j-constraints   - Generate Neo4j constraint DDL (Cypher)"
	@ echo "    neomodel            - Generate neomodel OGM classes"
	@ echo "    clean               - Remove generated artifacts"
	@ echo ""
	@ echo -e "  $(BUILD_PRINT)Docker:$(END_BUILD_PRINT)"
	@ echo "    up                  - Start services (docker compose up -d)"
	@ echo "    down                - Stop services (docker compose down)"
	@ echo "    down-volumes        - Stop services and remove volumes"
	@ echo "    rebuild             - Rebuild and start services"
	@ echo "    rebuild-clean       - Rebuild from scratch (no cache)"
	@ echo "    logs                - Follow service logs"
	@ echo "    ps                  - Show service status (docker compose ps)"
	@ echo ""
	@ echo -e "  $(BUILD_PRINT)Neo4j + MCP:$(END_BUILD_PRINT)"
	@ echo "    neo4j-shell         - Interactive Cypher shell (needs a TTY)"
	@ echo "    neo4j-wait          - Wait until Neo4j accepts Bolt connections"
	@ echo "    neo4j-schema        - Apply constraints + indexes (Community-safe subset)"
	@ echo "    neo4j-seed          - Load deterministic demo data"
	@ echo "    neo4j-queries       - Run demo Cypher queries"
	@ echo "    neo4j-reset         - DESTRUCTIVE: wipe all nodes, re-apply schema + seed"
	@ echo "    neo4j-browser       - Print the Neo4j Browser URL + credentials"
	@ echo "    mcp-logs            - Follow the MCP server logs"
	@ echo "    mcp-restart         - Restart the MCP server"
	@ echo ""
	@ echo -e "  $(BUILD_PRINT)Git hooks:$(END_BUILD_PRINT)"
	@ echo "    install-git-hooks   - Install the local pre-commit secret scan hook"
	@ echo ""
	@ echo -e "  $(BUILD_PRINT)CI / Quality gates:$(END_BUILD_PRINT)"
	@ echo "    install                  - Install project dependencies via Poetry"
	@ echo "    lint-python              - Lint Python source with Ruff"
	@ echo "    format-check-python      - Check Python formatting with Ruff (no changes)"
	@ echo "    format-python            - Apply Ruff formatting to Python source"
	@ echo "    typecheck                - Type-check with mypy"
	@ echo "    test-unit                - Run unit tests with coverage (fails under 80%)"
	@ echo "    check-architecture       - Enforce import boundaries with import-linter"
	@ echo "    operational-schemas      - Generate operational JSON schemas"
	@ echo "    check-model-generated    - Fail if model/generated is stale relative to the LinkML schema"
	@ echo "    check-operational-schemas - Fail if operational schemas are stale"
	@ echo "    check-secrets            - Scan tracked files for committed secrets"
	@ echo "    test-integration         - Run integration-marked tests"
	@ echo "    test-system              - Run system-marked tests"
	@ echo "    test-bdd                 - Run BDD step-definition tests"
	@ echo "    test-evaluation-recorded - Run recorded-model evaluation tests (no live calls)"
	@ echo "    test-evaluation-live     - Run live-model evaluation tests (opt-in, calls the real model)"
	@ echo "    test-evaluation-judge    - Run the LLM-judge clarification evaluation (opt-in, calls the real model)"
	@ echo "    ci-static                - Run static quality gates (lint)"
	@ echo "    ci-acceptance            - Integration + system + BDD tests + evidence report"
	@ echo "    ci                       - Full CI pipeline (static + acceptance)"
	@ echo "    release-evidence         - Build the Change 1 release evidence report"
	@ echo ""

# Every artifact lands under a single tree: $(GEN)/<target>/...; all diagrams
# (ER, PlantUML UML, whole-model class) go under $(DIAG).
all: lint pydantic owl shacl jsonschema erdiagram plantuml classdiagram neo4j-constraints neomodel

lint:
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Linting LinkML schema$(END_BUILD_PRINT)"
	@ poetry run linkml-lint -c .linkmllint.yaml $(SCHEMA)
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Lint complete$(END_BUILD_PRINT)"

# Pydantic classes (the "possibly generate pydantic" target).
pydantic:
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Generating Pydantic classes$(END_BUILD_PRINT)"
	@ mkdir -p $(GEN)/pydantic && poetry run gen-pydantic $(SCHEMA) > $(GEN)/pydantic/hulubul_models.py
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Pydantic classes generated$(END_BUILD_PRINT)"

# Ontology + constraints. Every class/slot carries an explicit hlb: URI, so the
# OWL/SHACL come out complete even though the shipped targets are Python/Neo4j.
owl:
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Generating OWL ontology$(END_BUILD_PRINT)"
	@ mkdir -p $(GEN)/owl && poetry run gen-owl $(SCHEMA) > $(GEN)/owl/hulubul.owl.ttl
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) OWL ontology generated$(END_BUILD_PRINT)"

shacl:
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Generating SHACL shapes$(END_BUILD_PRINT)"
	@ mkdir -p $(GEN)/shacl && poetry run gen-shacl $(SCHEMA) > $(GEN)/shacl/hulubul.shacl.ttl
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) SHACL shapes generated$(END_BUILD_PRINT)"

jsonschema:
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Generating JSON Schema$(END_BUILD_PRINT)"
	@ mkdir -p $(GEN)/jsonschema && poetry run gen-json-schema $(SCHEMA) > $(GEN)/jsonschema/hulubul.schema.json
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) JSON Schema generated$(END_BUILD_PRINT)"

# ER diagram (Mermaid, whole model).
erdiagram:
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Generating ER diagram$(END_BUILD_PRINT)"
	@ mkdir -p $(DIAG) && poetry run gen-erdiagram $(SCHEMA) > $(DIAG)/hulubul.er.md
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) ER diagram generated$(END_BUILD_PRINT)"

# UML class diagram (PlantUML, whole model) — renders via any PlantUML tool/plugin.
plantuml:
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Generating PlantUML diagram$(END_BUILD_PRINT)"
	@ mkdir -p $(DIAG) && poetry run gen-plantuml $(SCHEMA) > $(DIAG)/hulubul.puml
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) PlantUML diagram generated$(END_BUILD_PRINT)"

# Whole-model UML class diagram as a single Mermaid .md (renders on GitHub).
# Custom generator — LinkML only emits per-class; see scripts/gen_mermaid_classdiagram.py.
classdiagram:
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Generating whole-model class diagram$(END_BUILD_PRINT)"
	@ mkdir -p $(DIAG) && poetry run python scripts/gen_mermaid_classdiagram.py $(SCHEMA) > $(DIAG)/hulubul.class.md
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Class diagram generated$(END_BUILD_PRINT)"

# Neo4j is loaded via linkml-store, not a codegen target:
#   https://linkml.io/linkml-store/how-to/Use-Neo4j.html
# Entity classes carry `id` (identifier) -> Neo4j nodes; object-valued slots are
# `inlined: false` -> Neo4j relationships. Value objects (GeoCoordinates) have no
# id and are embedded. Example load:
#   linkml-store -d neo4j://localhost:7687 insert -i data.yaml --schema $(SCHEMA)
#
# neomodel (https://neomodel.readthedocs.io) is a separate Neo4j OGM. LinkML ships
# no neomodel generator, so we provide one: scripts/gen_neomodel.py (Generator
# subclass + Jinja2 template) — see the `neomodel` target below.
neo4j:
	@ echo "Load instances with linkml-store: linkml-store ... insert --schema $(SCHEMA)"
	@ echo "No neomodel generator exists in LinkML — see Makefile comment."

# Neo4j constraint DDL for the enforceable subset (identifier -> uniqueness;
# required/typed scalars -> existence/type on Enterprise). Custom generator built
# on linkml.utils.generator.Generator — see scripts/gen_neo4j_constraints.py.
neo4j-constraints:
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Generating Neo4j constraints$(END_BUILD_PRINT)"
	@ mkdir -p $(GEN)/neo4j && poetry run python scripts/gen_neo4j_constraints.py $(SCHEMA) > $(GEN)/neo4j/constraints.cypher
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Neo4j constraints generated$(END_BUILD_PRINT)"

# neomodel OGM classes (StructuredNode + RelationshipTo). Custom generator built
# on linkml.utils.generator.Generator + Jinja2 — see scripts/gen_neomodel.py.
neomodel:
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Generating neomodel OGM classes$(END_BUILD_PRINT)"
	@ mkdir -p $(GEN)/neomodel && poetry run python scripts/gen_neomodel.py $(SCHEMA) > $(GEN)/neomodel/hulubul_ogm.py
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) neomodel OGM classes generated$(END_BUILD_PRINT)"

clean: ## Remove generated artifacts
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Removing generated artifacts$(END_BUILD_PRINT)"
	@ rm -rf $(GEN)
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Clean complete$(END_BUILD_PRINT)"

#-----------------------------------------------------------------------------
# Docker
#-----------------------------------------------------------------------------
.PHONY: check-env up down down-volumes rebuild rebuild-clean logs ps

check-env:
	@ test -f $(ENV_FILE) || (echo -e "$(BUILD_PRINT)$(ICON_ERROR) Missing $(ENV_FILE). Run: cp infra/.env.example infra/.env$(END_BUILD_PRINT)" && exit 1)

up: check-env ## Start services (docker compose up -d)
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Starting services$(END_BUILD_PRINT)"
	@ docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) up -d
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Services started$(END_BUILD_PRINT)"

down: check-env ## Stop services (docker compose down)
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Stopping services$(END_BUILD_PRINT)"
	@ docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) down
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Services stopped$(END_BUILD_PRINT)"

down-volumes: check-env ## Stop services and remove volumes
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Stopping services and removing volumes$(END_BUILD_PRINT)"
	@ docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) down -v
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Services stopped and volumes removed$(END_BUILD_PRINT)"

rebuild: check-env ## Rebuild and start services
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Rebuilding services$(END_BUILD_PRINT)"
	@ docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) up -d --build
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Services rebuilt and started$(END_BUILD_PRINT)"

rebuild-clean: check-env ## Rebuild from scratch (no cache) and start services
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Rebuilding services (no cache)$(END_BUILD_PRINT)"
	@ docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) build --no-cache
	@ docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) up -d
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Services rebuilt (clean) and started$(END_BUILD_PRINT)"

logs: check-env ## Follow service logs
	@ docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) logs -f

ps: check-env ## Show service status (docker compose ps)
	@ docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) ps

#-----------------------------------------------------------------------------
# Neo4j + MCP
# All targets use the cypher-shell bundled in the neo4j image, so no local
# Neo4j client is required. Credentials come from .env (see NEO4J_PW above).
#-----------------------------------------------------------------------------
.PHONY: neo4j-shell neo4j-wait neo4j-schema neo4j-seed neo4j-reset neo4j-queries neo4j-browser mcp-logs mcp-restart

neo4j-wait: check-env ## Wait until Neo4j accepts Bolt connections
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Waiting for Neo4j$(END_BUILD_PRINT)"
	@ for i in $$(seq 1 60); do \
		$(NEO4J_RUN) 'RETURN 1' >/dev/null 2>&1 && { echo -e "$(BUILD_PRINT)$(ICON_DONE) Neo4j ready$(END_BUILD_PRINT)"; exit 0; }; \
		sleep 2; \
	done; echo -e "$(BUILD_PRINT)$(ICON_ERROR) Neo4j not ready after 120s$(END_BUILD_PRINT)"; exit 1

neo4j-schema: check-env ## Apply constraints + indexes (Community-safe subset)
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Applying Neo4j schema$(END_BUILD_PRINT)"
	@ bash $(INFRA_PATH)/scripts/neo4j-setup-schema.sh
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Schema applied$(END_BUILD_PRINT)"

neo4j-seed: check-env ## Load deterministic demo data
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Seeding Neo4j$(END_BUILD_PRINT)"
	@ bash $(INFRA_PATH)/scripts/neo4j-seed.sh
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Neo4j seeded$(END_BUILD_PRINT)"

neo4j-queries: check-env ## Run demo Cypher queries
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Running demo queries$(END_BUILD_PRINT)"
	@ $(NEO4J_RUN) < $(NEO4J_CY)/demo-queries.cypher
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Demo queries complete$(END_BUILD_PRINT)"

neo4j-reset: check-env ## DESTRUCTIVE: wipe all nodes, re-apply schema + seed
	@ echo -e "$(BUILD_PRINT)$(ICON_WARNING) This will DELETE all nodes and relationships in Neo4j.$(END_BUILD_PRINT)"
	@ read -r -p "Type 'yes' to proceed: " ans; [ "$$ans" = "yes" ] || { echo "Aborted."; exit 1; }
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Wiping graph$(END_BUILD_PRINT)"
	@ $(NEO4J_RUN) 'MATCH (n) DETACH DELETE n;'
	@ bash $(INFRA_PATH)/scripts/neo4j-setup-schema.sh
	@ bash $(INFRA_PATH)/scripts/neo4j-seed.sh
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Neo4j reset (wipe + schema + seed)$(END_BUILD_PRINT)"

neo4j-shell: check-env ## Interactive Cypher shell (needs a TTY)
	@ docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) exec \
	  --env NEO4J_USERNAME=$(NEO4J_USR) --env NEO4J_PASSWORD=$(NEO4J_PW) \
	  neo4j cypher-shell -u $(NEO4J_USR)

neo4j-browser: ## Print the Neo4j Browser URL + credentials
	@ echo "Neo4j Browser: http://localhost:7474  (user: $(NEO4J_USR), password: $(NEO4J_PW))"

mcp-logs: check-env ## Follow the MCP server logs
	@ docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) logs -f mcp-neo4j

mcp-restart: check-env ## Restart the MCP server
	@ docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) restart mcp-neo4j

#-----------------------------------------------------------------------------
# Git hooks
#-----------------------------------------------------------------------------
.PHONY: install-git-hooks

install-git-hooks: ## Install the local pre-commit secret scan hook
	@ install -m 755 scripts/git-hooks/pre-commit "$$(git rev-parse --git-common-dir)/hooks/pre-commit"
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Installed pre-commit hook (runs check_committed_secrets.py)$(END_BUILD_PRINT)"

#-----------------------------------------------------------------------------
# Python quality, tests and CI
# Namespaced so they never collide with the LinkML generation targets above:
# `lint` stays LinkML-only (linkml-lint); Python style/type checks live under
# `lint-python`/`typecheck`. Targets whose source scripts/tests are introduced
# by later plan tasks fail naturally until those tasks land — that is
# expected, not a bug in this target set.
#-----------------------------------------------------------------------------
.PHONY: install lint-python format-check-python typecheck test-unit \
	check-architecture operational-schemas format-python check-model-generated \
	check-operational-schemas check-secrets test-integration \
	test-system test-bdd test-evaluation-recorded test-evaluation-live \
	test-evaluation-judge ci-static ci-acceptance ci acceptance-up \
	acceptance-ready acceptance-deploy preflight-langflow-1-10-2 \
	acceptance-diagnostics acceptance-down release-evidence

install: ## Install all dependency groups (test, quality, langflow, integration)
	poetry install --with test,quality,langflow,integration

lint-python: ## Lint Python source with Ruff
	poetry run ruff check src tests scripts

format-check-python: ## Check Python formatting with Ruff (no changes)
	poetry run ruff format --check src tests scripts

format-python: ## Apply Ruff formatting to Python source
	poetry run ruff format src tests scripts

typecheck: ## Type-check with mypy
	poetry run mypy src/hulubul scripts tests

test-unit: ## Run unit tests with coverage (fails under 80%)
	@ mkdir -p reports
	poetry run pytest tests/unit --cov=hulubul --cov-branch --cov-fail-under=80 --junitxml=reports/junit-unit.xml

check-architecture: ## Enforce import boundaries with import-linter
	poetry run lint-imports

operational-schemas: ## Generate operational JSON schemas
	poetry run gen-operational-schemas --output schemas/operational/v1

check-model-generated: lint pydantic jsonschema erdiagram plantuml classdiagram neo4j-constraints neomodel ## Fail if model/generated is stale relative to the LinkML schema
	git diff --exit-code -- model/generated ':(exclude)model/generated/owl/**' ':(exclude)model/generated/shacl/**'

check-operational-schemas: ## Fail if operational schemas are stale
	poetry run gen-operational-schemas --output schemas/operational/v1 --check

check-secrets: ## Scan tracked files for committed secrets
	poetry run python scripts/check_committed_secrets.py

# check-flows: ## Validate LangFlow flow assets (normalize, manifest, lfx checks)
# 	poetry run python scripts/normalize_langflow_flows.py --check langflow/flows/*.json
# 	poetry run python scripts/validate_langflow_assets.py langflow/flow-manifest.yaml
# 	poetry run lfx validate --level 4 --strict --skip-credentials langflow/flows/*.json
# 	for flow in langflow/flows/*.json; do poetry run lfx upgrade --strict "$$flow"; done

test-integration: ## Run integration-marked tests
	poetry run pytest -m integration

test-system: ## Run system-marked tests
	poetry run pytest -m system

test-bdd: ## Run BDD step-definition tests
	poetry run pytest tests/steps/test_delivery_request_intake.py tests/steps/test_conversation_resumption.py

# test-evaluation-recorded: ## Run recorded-model evaluation tests (no live calls)
# 	poetry run pytest tests/evaluation/test_dataset_contract.py tests/evaluation/test_recorded_intake_evaluation.py

# test-evaluation-live: ## Run live-model evaluation tests (opt-in, calls the real model)
# 	poetry run pytest tests/evaluation/test_live_intake_evaluation.py --run-live-evaluation

# test-evaluation-judge: ## Run the LLM-judge clarification evaluation (opt-in, calls the real model)
# 	poetry run pytest tests/evaluation/test_clarification_judge.py --run-live-evaluation

# Static CI: schema + Python quality + fast tests (no comment on the target
# line itself, so the prerequisite list stays exactly the canonical set).
ci-static: lint check-model-generated lint-python format-check-python typecheck check-architecture check-operational-schemas check-secrets test-unit

# Acceptance CI: integration + system + BDD tests + evidence report.
ci-acceptance: test-integration test-system test-bdd release-evidence

# Full CI pipeline (static + acceptance).
ci: ci-static ci-acceptance

ACCEPTANCE_PROJECT ?= hulubul-change1-$${USER}
ACCEPTANCE_COMPOSE = docker compose -p $(ACCEPTANCE_PROJECT) -f infra/docker-compose.yaml -f infra/docker-compose.test.yaml

acceptance-up: ## Start the acceptance Docker stack (Postgres, Neo4j, MCP, recorded model, LangFlow)
	$(ACCEPTANCE_COMPOSE) up -d --build postgres neo4j neo4j-schema mcp-neo4j recorded-model langflow

acceptance-ready: ## Wait for the acceptance stack to report ready, in dependency order
	poetry run pytest tests/integration/runtime/test_readiness_order.py -q

acceptance-deploy: ## Push validated LangFlow flows to the acceptance environment
	cd langflow && lfx push --env ci --no-normalize --keep-secrets flows/10-lf-70-data-access.json
	cd langflow && lfx push --env ci --no-normalize --keep-secrets flows/20-lf-10-request-intake.json
	cd langflow && lfx push --env ci --no-normalize --keep-secrets flows/30-lf-00-main-router.json

preflight-langflow-1-10-2: ## Verify LangFlow 1.10.2 persistence/trace/recorded-model compatibility
	poetry run pytest tests/integration/langflow/test_langflow_persistence_contract.py tests/integration/langflow/test_recorded_model_compatibility.py tests/integration/langflow/test_native_trace_contract.py -q

acceptance-diagnostics: ## Collect acceptance-stack diagnostics only (no evidence assertions)
	poetry run python scripts/build_change1_evidence.py --diagnostics-only --output reports/change1/diagnostics.json

acceptance-down: ## Tear down the acceptance Docker stack and its volumes
	$(ACCEPTANCE_COMPOSE) down -v --remove-orphans

release-evidence: ## Build the Change 1 release evidence report
	poetry run python scripts/build_change1_evidence.py --output reports/change1/release-evidence.json

# Default target
.DEFAULT_GOAL := help
