# Hulubul V1 — Infrastructure

Local stack for the **autonomous agent-driven parcel broker**. Brings up the
agent orchestrator (Langflow), the **graph system of record (Neo4j)**, and the
**Neo4j MCP server** that exposes the graph to agents over the Model Context
Protocol.

The design follows the architecture ADRs (`../architecture/decisions/README.md`):

- **ADR-005** — Neo4j is the system of record; agents reach it via MCP.
- **ADR-015** — the **party path** uses a *custom scoped* MCP (deferred,
  modelling-blocked); the **admin path** uses the stock Neo4j Labs MCP server,
  audited. This stack ships only the **admin path**.
- **ADR-016** — low-code orchestration (Langflow) over a minimal Python core.

## Architecture

```
  Langflow (orchestration, :7860)
        │  MCP Tools component (HTTP)
        ▼
  mcp-neo4j (MCP server, :8000)  ── admin-style, audited path (ADR-007/015)
        │  Bolt
        ▼
  Neo4j Community 5 + APOC (:7474 Browser, :7687 Bolt)  ── graph system of record
        │
        ├─ infra/cypher/schema.cypher   (constraints + indexes)
        └─ infra/cypher/seed.cypher      (deterministic demo data)

  Postgres (:5432)  ── Langflow's own metadata store.
```

The MCP server is the **only** thing that should point an agent at Neo4j in this
setup. There is no bespoke data-access code yet; the party-facing scoped MCP is
out of scope (see *Security*).

## Services & ports

| Service    | Image / build          | Host port(s) | Purpose                                                |
|------------|------------------------|--------------|--------------------------------------------------------|
| `neo4j`    | `neo4j:5.26-community` | 7474, 7687   | Graph DB (Browser 7474, Bolt 7687). APOC enabled.      |
| `mcp-neo4j`| `./mcp` (python 3.12)  | 8000         | Neo4j Labs MCP server (streamable HTTP at `/mcp/`).    |
| `langflow` | `langflowai/langflow`  | 7860         | Low-code agent orchestration.                          |
| `postgres` | `postgres:16`          | — (internal) | Langflow metadata.                                     |

## Environment

All configuration lives in `infra/.env` (gitignored). Copy the example first:

```bash
cp infra/.env.example infra/.env   # then edit passwords
```

| Variable               | Default        | Meaning                                                              |
|------------------------|----------------|----------------------------------------------------------------------|
| `POSTGRES_PASSWORD`    | `changeme`     | Langflow's Postgres password.                                        |
| `NEO4J_PASSWORD`       | `changeme123`  | Neo4j `neo4j` user password (≥ 8 chars; set at first boot).          |
| `NEO4J_USERNAME`       | `neo4j`        | Neo4j user used by the MCP server / scripts.                         |
| `NEO4J_DATABASE`       | `neo4j`        | Neo4j database name (Community has a single DB).                     |
| `NEO4J_MCP_PORT`       | `8000`         | Host port for the MCP server.                                        |
| `NEO4J_MCP_READ_ONLY`  | `false`        | MCP server read-only flag. `false` = writable (admin path). `true` = read-only. |

> Changing `NEO4J_PASSWORD` after the first run does **not** re-set the password
> (Neo4j stores it in the volume). To reset: `make down-volumes` and start fresh.

## Quickstart

From the repo root:

```bash
cp infra/.env.example infra/.env     # one-time, edit passwords
make up                              # start Neo4j + MCP + Langflow + Postgres
make neo4j-schema                    # constraints + indexes (Community-safe)
make neo4j-seed                      # deterministic demo data
make neo4j-queries                   # run the demo Cypher queries
make neo4j-browser                   # print the Browser URL + credentials
```

Other handy targets:

```bash
make neo4j-shell      # interactive Cypher shell (needs a TTY)
make neo4j-reset      # DESTRUCTIVE: wipe all nodes, re-apply schema + seed
make mcp-logs         # follow the MCP server logs
make mcp-restart      # restart the MCP server (picks up Neo4j restart)
make logs             # all services
make down             # stop (keeps volumes/data)
make down-volumes     # stop and DELETE all data (Neo4j + Postgres)
```

## Wiring the MCP server into Langflow

The MCP server speaks **MCP over streamable HTTP** at:

```
http://localhost:8000/mcp/
```

(Note the trailing slash — the path is configurable via `NEO4J_MCP_SERVER_PATH`.)

In Langflow:

1. Open the canvas (auto-login is enabled → http://localhost:7860).
2. Add an **MCP Tools** (or "MCP") component to a flow.
3. Set the transport to **Streamable HTTP** / `http` and the URL to
   `http://mcp-neo4j:8000/mcp/` from a *Langflow-side* flow (services share the
   compose network, so use the service name `mcp-neo4j`, not `localhost`).
   Use `http://localhost:8000/mcp/` only when running a client **on the host**.
4. The component will list the server's tools (see below). Wire one into an
   Agent component as a tool.

Tools exposed by `mcp-neo4j-cypher` (the admin path — unguarded), verified with
an MCP client over streamable HTTP:

| Tool                  | What it does                                                  |
|-----------------------|---------------------------------------------------------------|
| `read_neo4j_cypher`   | Run a read Cypher query (read transaction).                   |
| `write_neo4j_cypher`  | Run a write Cypher query (write transaction). *(writable mode)*|
| `get_neo4j_schema`    | Introspect the graph schema (needs APOC → enabled).           |

Tool names are version-dependent (Labs/beta) — re-verify on upgrade (see below).

> A ready-to-import Langflow flow JSON that wraps `get_neo4j_schema` +
> `read_neo4j_cypher` behind a guardrail is a **follow-up** (out of scope here).
> This stack provides the MCP endpoint and the data only.

## Files

```
infra/
├── docker-compose.yaml        # neo4j + mcp-neo4j + langflow + postgres
├── .env.example               # committed template (copy to .env)
├── langflow.env               # Langflow LLM/model env (gitignored)
├── mcp/
│   ├── Dockerfile             # python:3.12-slim + mcp-neo4j-cypher
│   └── requirements.txt       # pinned mcp-neo4j-cypher==0.6.0
├── scripts/
│   ├── neo4j-common.sh        # shared: load .env, cypher-shell exec, wait
│   ├── neo4j-setup-schema.sh  # apply schema.cypher (+ wait for Neo4j)
│   └── neo4j-seed.sh          # load seed.cypher (+ wait for Neo4j)
└── cypher/
    ├── schema.cypher          # Community-safe uniqueness + range indexes
    ├── seed.cypher            # deterministic demo fixtures (MERGE by id)
    └── demo-queries.cypher    # Q1–Q9 retrieval demos (make neo4j-queries)
```

### Where the schema comes from

The **uniqueness constraints** in `cypher/schema.cypher` mirror the `IS UNIQUE`
lines of `../model/generated/neo4j/constraints.cypher`, which is generated from
the LinkML source of truth (`../model/linkml/`) by:

```bash
make neo4j-constraints     # regenerate model/generated/neo4j/constraints.cypher
```

The generated file also contains **Enterprise-only** constraints (`IS NOT NULL`,
`IS :: TYPE`) which Neo4j Community cannot enforce; `cypher/schema.cypher`
applies only the Community-safe subset and adds hand-maintained **range indexes**
on hot query properties (access paths are not part of the model, so they are not
generated). If you upgrade to Neo4j Enterprise, you can apply the full generated
file instead.

The domain labels/relationships/properties match the OGM at
`../model/generated/neomodel/hulubul_ogm.py` (regenerate with `make neomodel`).

## Security

This is the **admin path** and is **not safe for party-facing traffic**:

- **Neo4j Community has no in-engine RBAC** and a single database (ADR-015). The
  DB itself cannot confine a client to "their data".
- The MCP server is **writable** by default (`NEO4J_MCP_READ_ONLY=false`) and the
  `write_neo4j_cypher` tool runs arbitrary Cypher. There is **no guardrail**
  here — this is the raw, audited admin surface, not the party path.
- Party-facing agents must **not** receive this MCP endpoint. They will receive
  the future **custom scoped MCP/tool server** (ADR-015, modelling-blocked) that
  exposes only named, per-party-scoped operations over the service layer, with
  the party id bound server-side from the authenticated session.
- Until that scoped MCP exists, treat the whole graph as admin-only.

To lock the MCP server to read-only queries for a demo, set
`NEO4J_MCP_READ_ONLY=true` in `infra/.env` and `make mcp-restart` (or rebuild).

## Re-verify on upgrade

`mcp-neo4j-cypher` is **Labs/beta** grade (`../architecture/task-2-frameworks-exploration.md`
§8). On upgrade, re-verify the tool names, transport options and read-only
behaviour against its release notes, and re-pin in `mcp/requirements.txt`.
