# LangFlow's two invocation mechanisms

Referenced from `AGENTS.md` § "Langflow MCP (flow debugging)". Read this when
you need to reproduce or verify a bug reported from the LangFlow Playground
UI, or when a repro attempt doesn't reproduce what the developer is seeing.

## The two mechanisms

- **Plain run** — `POST /api/v1/run/{flow_id}`. Synchronous, single request/
  response, no tracing wired in. This is what a scripted `curl`/`requests`
  call defaults to, and what `run_flow` (langflow MCP) and
  `HulubulLf70FlowTool`/`HulubulRunFlowComponent`'s own cross-flow calls use.
- **Streaming build** — `POST /api/v1/build/{flow_id}/flow` (returns a
  `job_id`) then `GET /api/v1/build/{job_id}/events` (Server-Sent Events,
  streamed per-vertex progress). **This is what the Playground UI actually
  uses.** It wires in LangFlow's own tracing service (`NativeTracer`), which
  the plain run path does not.

## Why this matters

Confirmed live, twice in the same investigation (see git history for
`fix(langflow): protect per-tool-call deepcopy...` and
`fix(langflow): make Playground session UUID mapping deterministic`): a bug
reproduced 100% of the time via the streaming path and 0% of the time via
20+ plain-run attempts with the same flow and the same input. The
differences that matter for repro:

| | Plain run | Streaming build |
|---|---|---|
| Tracing wired in | No | Yes — can leak live objects (e.g. an `asyncio.Task`) into a component's cached state |
| Session label | Whatever you pass — always use a real UUID unless testing the label-normalization path itself | Sends the raw Playground display label (e.g. `"New Session 0"`), not a UUID |

**Rule of thumb:** if a developer reports a bug from the Playground UI that a
plain-run repro attempt doesn't reproduce, don't conclude the bug is fixed or
non-deterministic — reproduce via the streaming build mechanism before
drawing either conclusion.

## Minimal repro

```python
import requests

payload = {"inputs": {"input_value": "...", "session": "New Session 0", "type": "chat"}}
r = requests.post(f"{BASE_URL}/api/v1/build/{flow_id}/flow", headers=headers, json=payload, timeout=60)
job_id = r.json()["job_id"]

events = requests.get(f"{BASE_URL}/api/v1/build/{job_id}/events", headers=headers, stream=True, timeout=280)
for line in events.iter_lines():
    if line:
        evt = json.loads(line)  # event types: vertices_sorted, build_start, end_vertex, log, error, build_end, add_message, end
```

## Multi-turn conversations

Run turns **sequentially** (wait for one turn's events stream to finish
before sending the next) — firing multiple `/build` calls back-to-back
without waiting does not reproduce a real conversation and can interleave
state incorrectly.

## Disconnecting from `/events` cancels the job server-side

Confirmed live: if the client reading `GET /api/v1/build/{job_id}/events`
disconnects or times out before the stream ends, LangFlow **cancels the job**
(`docker logs` shows `"Build cancelled"` / `"Job ... was cancelled by
system"` immediately after). This is different from the plain `/run/`
endpoint, where a client-side timeout does not necessarily stop server-side
processing.

Practical consequence when reproducing or verifying a slow multi-turn flow:
a turn that legitimately takes several minutes (this system has observed
single turns take 15-20+ minutes under upstream-model-timeout/retry
conditions) will never complete if your `/events` read times out first — you
won't get a slow result, you'll get no result, and the job is gone for good.
Set the `/events` request's timeout generously (minutes, not the ~60-280s
that's fine for a single-shot request), or run it in the background with a
long timeout, rather than assuming a stalled-looking request is still
progressing server-side the way it would on `/run/`.
