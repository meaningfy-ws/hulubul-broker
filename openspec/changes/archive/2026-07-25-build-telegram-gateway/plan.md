# Telegram Channel Gateway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Telegram gateway process that receives inbound Telegram messages, derives a deterministic session_id, calls LangFlow's Run API with a trusted channel identity, and relays the reply back — with a `ChannelPort` interface a future WhatsApp adapter can implement without touching the gateway core.

**Architecture:** Cosmic-python layered bounded context (`src/hulubul/channel_gateway/`): pure `models/` value objects (`InboundMessage`, `Channel`, `derive_session_id`), `adapters/` implementing `ChannelPort` (Telegram via aiogram, WhatsApp as a stub) plus a `LangflowClient` HTTP adapter, one `services/relay_message.py` orchestrating the round trip, and a `telegram_bot.py` process entrypoint. New Docker Compose service + ngrok tunnel for local webhook testing.

**Tech Stack:** Python 3.10+, aiogram 3.x, httpx (async), pytest + pytest-bdd, mypy, import-linter, Docker Compose, ngrok.

## Global Constraints

- Python version: `>=3.10,<3.15` (existing `pyproject.toml` floor) — no syntax newer than 3.10 allows.
- New Poetry group `gateway` is **optional** (mirrors `test`/`quality`/`integration`/`langflow`) — never a base dependency.
- `models/` MUST NOT import `adapters/`, `services/`, or `entrypoints/`. `adapters/` MUST NOT import `services/` or `entrypoints/`. `services/` MUST NOT import `entrypoints/`. Enforced via `.importlinter`.
- No live WhatsApp API calls anywhere in this plan — `WhatsAppAdapter` methods raise `NotImplementedError`.
- No Telegram bot token, webhook secret, or any credential committed to git — always via `infra/.env` (gitignored) or environment variables.
- Coverage target: ≥80% on the new `channel_gateway` package (existing repo-wide `fail_under = 80` in `pyproject.toml`).
- `tests/e2e/` MUST NOT run in CI — CI runs `tests/unit/` and `tests/feature/` only.

---

### Task 0: Relocate LinkML→Pydantic generation into an importable domain package

**Files:**
- Modify: `Makefile` (`pydantic` target, `check-model-generated` target)
- Modify: `AGENTS.md` (generated-artifacts convention note)
- Modify: `architecture/decisions/README.md` (ADR-019: table row + full entry)
- Create: `src/hulubul/core/models/domain/__init__.py`
- Create: `tests/unit/hulubul/core/models/test_domain_generated.py`
- Delete: `model/generated/pydantic/hulubul_models.py` (old location, superseded)

**Interfaces:**
- Produces: `hulubul.core.models.domain.hulubul_models` — a generated, importable module
  (`Channel`, `Medium`, `ChannelValidationStatus`, and every other LinkML-derived class),
  consumed by Task 2 (`Medium` reuse) and Task 3 (`ChannelRef`/`Medium` reuse), and by any
  future bounded context needing a domain entity.

Currently `model/generated/pydantic/hulubul_models.py` is **not** part of the installed
`hulubul` package (`pyproject.toml`'s `packages` list only includes `src/hulubul`), so
nothing under `src/hulubul/` can import it without a path hack. This task makes the
generated domain models a normal, reusable import — `from hulubul.core.models.domain.hulubul_models import Channel, Medium` — while keeping them clearly generated (never hand-edited),
consistent with `model/generated/`'s existing "never hand-edit, `make` overwrites" rule.

- [ ] **Step 1: Write a failing importability test**

```python
# tests/unit/hulubul/core/models/test_domain_generated.py
from hulubul.core.models.domain.hulubul_models import Channel, ChannelValidationStatus, Medium


def test_medium_has_the_full_permissible_value_set():
    assert {m.value for m in Medium} == {"GSM", "WhatsApp", "Telegram", "Viber", "email"}


def test_channel_requires_id_system_id_medium_and_validation_status():
    channel = Channel(
        id="channel-123",
        systemID="987654321",
        hasMedium=Medium.Telegram,
        validationStatus=ChannelValidationStatus.valid,
    )
    assert channel.id == "channel-123"
    assert channel.alias is None  # optional fields still default to None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/unit/hulubul/core/models/test_domain_generated.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hulubul.core.models.domain'`

- [ ] **Step 3: Update the Makefile's `pydantic` target to write into the domain package**

In `Makefile`, add a new path variable near the existing `GEN`/`DIAG` definitions:

```makefile
DOMAIN_MODELS := $(REPO_ROOT)/src/hulubul/core/models/domain
```

Replace the `pydantic` target:

```makefile
pydantic:
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Generating Pydantic classes$(END_BUILD_PRINT)"
	@ mkdir -p $(DOMAIN_MODELS) && poetry run gen-pydantic $(SCHEMA) > $(DOMAIN_MODELS)/hulubul_models.py
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Pydantic classes generated$(END_BUILD_PRINT)"
```

Update the `check-model-generated` target's git-diff exclusion to point at the new location
(preserving today's behavior — pydantic output stays excluded from the staleness check; *why*
it was originally excluded, per commit `7a4981e`, hasn't been re-verified here and should be
checked before ever re-enabling the check on the new path):

```makefile
check-model-generated: lint pydantic jsonschema erdiagram plantuml classdiagram neo4j-constraints neomodel
	git diff --exit-code -- model/generated ':(exclude)model/generated/owl/**' ':(exclude)model/generated/shacl/**' src/hulubul/core/models/domain ':(exclude)src/hulubul/core/models/domain/**'
```

- [ ] **Step 4: Create the package `__init__.py` with a generated-content banner**

```python
# src/hulubul/core/models/domain/__init__.py
"""Domain models generated from model/linkml/ via `make pydantic`.

Never hand-edit anything in this package — the next `make pydantic` run
overwrites it. Edit the LinkML source under model/linkml/ instead.
"""
```

- [ ] **Step 5: Regenerate and remove the old location**

```bash
make pydantic
git rm model/generated/pydantic/hulubul_models.py
rmdir model/generated/pydantic 2>/dev/null || true
```

- [ ] **Step 6: Run test to verify it passes**

Run: `poetry run pytest tests/unit/hulubul/core/models/test_domain_generated.py -v`
Expected: PASS (2 tests)

- [ ] **Step 7: Update `AGENTS.md`'s generated-artifacts convention note**

Add a sentence to the existing "LinkML is the single source of truth" bullet noting that
`src/hulubul/core/models/domain/` is also `make`-generated and must never be hand-edited,
alongside `model/generated/`.

- [ ] **Step 8: Add ADR-019 to `architecture/decisions/README.md`**

This is a system-wide decision (every future bounded context benefits from generated domain
models actually being importable), not gateway-specific — it belongs in the ADR registry,
not only in this change's own design.md.

Add a row to the ADR summary table, immediately after the `ADR-018` row:

```markdown
| ADR-019 | L2 | Generated domain models land in an importable package (`hulubul.core.models.domain`), not orphaned under `model/generated/` | Proposed |
```

Add the full entry at the end of the file, after `## ADR-018 — ...`:

```markdown
---

## ADR-019 — Generated domain models land in an importable package (L2)

**Context.** LinkML is the single source of truth for Hulubul's domain model
(`model/linkml/`), and `make generate-models` derives Pydantic, OWL, SHACL, JSON Schema,
Cypher, and neomodel targets from it. Historically the Pydantic target wrote to
`model/generated/pydantic/hulubul_models.py`, which sits outside `pyproject.toml`'s
`packages` list (only `src/hulubul` is installed) — so no code under `src/hulubul/` could
import a generated domain class without a `sys.path` hack. This pushed hand-written code
toward silently redefining domain concepts instead of reusing them (observed twice while
building the Telegram channel gateway: the hand-written `core/models/operational/` layer,
and a first-draft local `Medium` enum that duplicated — incompletely — the real
LinkML-generated one).

**Decision.** `make pydantic`'s output moves to
`src/hulubul/core/models/domain/hulubul_models.py`, inside the installed package, so any
bounded context can `from hulubul.core.models.domain.hulubul_models import <Class>` with no
path manipulation. The file remains fully generated and is never hand-edited — regenerated
wholesale by `make pydantic`, with the same "never hand-edit, `make` overwrites" rule as
everything else under `model/generated/`. Only the Pydantic target moves; OWL/SHACL/JSON
Schema/diagrams/Cypher/neomodel outputs stay under `model/generated/` unchanged.

**Consequences.** +Generated domain models are actually reusable across bounded contexts,
closing the gap that caused at least two silent near-duplications. +Matches the Meaningfy
conceptual-modelling default ("generated artefacts land under the relevant package... via
`make generate-models`"), correcting a prior deviation from that standard. −A new bounded
context's `models/` layer can now contain both generated domain entities (imported, never
redefined) and hand-written operational value objects side by side — the boundary between
them must stay a live code-review discipline (survey `model/generated` →
`hulubul.core.models.domain` before hand-writing a new model), not something enforced by the
directory split alone. −The single-file generated output (`hulubul_models.py`, one file for
the whole merged schema) is unchanged by this decision; splitting into one generated file per
LinkML module remains a separate, unaddressed improvement.

**Confirmation.** `src/hulubul/core/models/domain/hulubul_models.py` exists, is importable
from any bounded context, and `model/generated/pydantic/` no longer exists as a separate,
unreachable copy.
```

- [ ] **Step 9: Commit**

```bash
git add Makefile AGENTS.md architecture/decisions/README.md src/hulubul/core/models/domain tests/unit/hulubul/core/models/test_domain_generated.py model/generated/pydantic
git commit -m "build(models): generate domain Pydantic models into an importable hulubul.core.models.domain package

Adds ADR-019."
```

---

### Task 1: Poetry `gateway` dependency group and package skeleton

**Files:**
- Modify: `pyproject.toml`
- Create: `src/hulubul/channel_gateway/__init__.py`
- Create: `src/hulubul/channel_gateway/models/__init__.py`
- Create: `src/hulubul/channel_gateway/adapters/__init__.py`
- Create: `src/hulubul/channel_gateway/services/__init__.py`
- Create: `src/hulubul/channel_gateway/entrypoints/__init__.py`
- Create: `tests/unit/hulubul/channel_gateway/__init__.py`
- Create: `tests/unit/hulubul/channel_gateway/models/__init__.py`
- Create: `tests/unit/hulubul/channel_gateway/adapters/__init__.py`
- Create: `tests/unit/hulubul/channel_gateway/services/__init__.py`
- Create: `tests/unit/hulubul/channel_gateway/entrypoints/__init__.py`

**Interfaces:**
- Produces: importable package `hulubul.channel_gateway` with four empty sub-packages, ready for Tasks 2–7.

- [ ] **Step 1: Add the `gateway` optional group to `pyproject.toml`**

Add after the existing `[tool.poetry.group.langflow.dependencies]` block:

```toml
[tool.poetry.group.gateway]
optional = true

[tool.poetry.group.gateway.dependencies]
aiogram = "3.15.0"
httpx = "0.28.1"
```

- [ ] **Step 2: Lock and install**

Run: `poetry lock && poetry install --with gateway,test`
Expected: resolves without conflicts, `poetry.lock` updated.

- [ ] **Step 3: Create the package skeleton**

```bash
mkdir -p src/hulubul/channel_gateway/{models,adapters,services,entrypoints}
touch src/hulubul/channel_gateway/__init__.py
touch src/hulubul/channel_gateway/models/__init__.py
touch src/hulubul/channel_gateway/adapters/__init__.py
touch src/hulubul/channel_gateway/services/__init__.py
touch src/hulubul/channel_gateway/entrypoints/__init__.py
mkdir -p tests/unit/hulubul/channel_gateway/{models,adapters,services,entrypoints}
touch tests/unit/hulubul/channel_gateway/__init__.py
touch tests/unit/hulubul/channel_gateway/models/__init__.py
touch tests/unit/hulubul/channel_gateway/adapters/__init__.py
touch tests/unit/hulubul/channel_gateway/services/__init__.py
touch tests/unit/hulubul/channel_gateway/entrypoints/__init__.py
```

- [ ] **Step 4: Verify the package imports**

Run: `python -c "import hulubul.channel_gateway"`
Expected: no error (empty package imports cleanly).

- [ ] **Step 5: Add import-linter contracts**

Open `.importlinter` and add (matching the existing contract style for `request_intake`):

```ini
[importlinter:contract:channel_gateway_layers]
name = channel_gateway layer boundaries
type = layers
layers =
    hulubul.channel_gateway.entrypoints
    hulubul.channel_gateway.services
    hulubul.channel_gateway.adapters
    hulubul.channel_gateway.models
containers =
    hulubul.channel_gateway
```

Run: `poetry run lint-imports`
Expected: PASS (no code yet to violate the contract).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml poetry.lock src/hulubul/channel_gateway tests/unit/hulubul/channel_gateway .importlinter
git commit -m "feat(channel-gateway): scaffold package skeleton and gateway dependency group"
```

---

### Task 2: Models — `InboundMessage`, `TextMessage`, `MediaMessage`

**Files:**
- Create: `src/hulubul/channel_gateway/models/message.py`
- Test: `tests/unit/hulubul/channel_gateway/models/test_message.py`

**Interfaces:**
- Consumes: `Medium` from `hulubul.core.models.domain.hulubul_models` (Task 0) — reused, not
  redefined, since it's already the real LinkML-generated enum (`GSM`, `WhatsApp`,
  `Telegram`, `Viber`, `email`).
- Produces: `InboundMessage(medium, system_id, text, reply_to_message_id=None)`,
  `TextMessage(text)`, `MediaMessage(url, caption=None)` — all frozen dataclasses, consumed
  by Tasks 3–6.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/hulubul/channel_gateway/models/test_message.py
from hulubul.core.models.domain.hulubul_models import Medium

from hulubul.channel_gateway.models.message import (
    InboundMessage,
    MediaMessage,
    TextMessage,
)


def test_inbound_message_is_immutable():
    msg = InboundMessage(medium=Medium.Telegram, system_id="123", text="hello")
    assert msg.medium is Medium.Telegram
    assert msg.system_id == "123"
    assert msg.text == "hello"
    assert msg.reply_to_message_id is None


def test_inbound_message_carries_reply_reference_when_present():
    msg = InboundMessage(
        medium=Medium.Telegram,
        system_id="123",
        text="yes",
        reply_to_message_id="987",
    )
    assert msg.reply_to_message_id == "987"


def test_text_message_holds_text():
    assert TextMessage(text="hi there").text == "hi there"


def test_media_message_caption_defaults_to_none():
    media = MediaMessage(url="https://example.com/photo.jpg")
    assert media.caption is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/unit/hulubul/channel_gateway/models/test_message.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hulubul.channel_gateway.models.message'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/hulubul/channel_gateway/models/message.py
from dataclasses import dataclass

from hulubul.core.models.domain.hulubul_models import Medium


@dataclass(frozen=True)
class InboundMessage:
    medium: Medium
    system_id: str
    text: str
    reply_to_message_id: str | None = None


@dataclass(frozen=True)
class TextMessage:
    text: str


@dataclass(frozen=True)
class MediaMessage:
    url: str
    caption: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/unit/hulubul/channel_gateway/models/test_message.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/hulubul/channel_gateway/models/message.py tests/unit/hulubul/channel_gateway/models/test_message.py
git commit -m "feat(channel-gateway): add InboundMessage/TextMessage/MediaMessage value objects"
```

---

### Task 3: Models — `ChannelRef` and `derive_session_id`

**Files:**
- Create: `src/hulubul/channel_gateway/models/channel.py`
- Test: `tests/unit/hulubul/channel_gateway/models/test_channel.py`

**Interfaces:**
- Consumes: `Medium` from `hulubul.core.models.domain.hulubul_models` (Task 0) — same real
  enum reused throughout, not redefined per module.
- Produces: `ChannelRef(medium, system_id)`, `derive_session_id(medium: Medium, system_id: str) -> str` — consumed by Task 6 (`LangflowClient`) and Task 7 (`relay_message`).

`ChannelRef` is an identity/reference value object (the `(medium, systemID)` natural key),
deliberately distinct from — and not to be confused with — the full `Channel` entity already
modeled in `model/linkml/hulubul_channel.yaml` and generated into
`hulubul.core.models.domain.hulubul_models` (Task 0). Two separate reasons the gateway
constructs `ChannelRef`, not `Channel`, at message-receipt time:
1. `Channel.validationStatus` is required, but the gateway *does* know the correct value —
   per the already-decided rule (an inbound message is itself proof of control) it would
   always be `valid`. This alone wouldn't block reusing `Channel` directly.
2. `Channel.id` is also required and is the **graph node identity** — meaningless before the
   node exists in Neo4j. The gateway cannot legitimately supply it without either minting a
   fake placeholder or taking over id-assignment from `resolve_channel_actor`. This is the
   actual blocker: a full `Channel` cannot honestly be constructed pre-persistence, so
   `ChannelRef` carries only what the gateway actually has. The real `Channel` (with a real
   `id` and `validationStatus`) is only ever constructed where a graph node backs it —
   inside `resolve_channel_actor`, not here. See design.md D7/D9.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/hulubul/channel_gateway/models/test_channel.py
from hulubul.core.models.domain.hulubul_models import Medium

from hulubul.channel_gateway.models.channel import ChannelRef, derive_session_id


def test_same_channel_always_derives_the_same_session_id():
    first = derive_session_id(Medium.Telegram, "123456789")
    second = derive_session_id(Medium.Telegram, "123456789")
    assert first == second


def test_different_media_never_collide_even_with_same_system_id():
    telegram_session = derive_session_id(Medium.Telegram, "15551234567")
    whatsapp_session = derive_session_id(Medium.WhatsApp, "15551234567")
    assert telegram_session != whatsapp_session


def test_session_id_is_a_plain_deterministic_string():
    assert derive_session_id(Medium.Telegram, "42") == "Telegram:42"


def test_channel_ref_holds_medium_and_system_id():
    channel_ref = ChannelRef(medium=Medium.WhatsApp, system_id="+15551234567")
    assert channel_ref.medium is Medium.WhatsApp
    assert channel_ref.system_id == "+15551234567"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/unit/hulubul/channel_gateway/models/test_channel.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hulubul.channel_gateway.models.channel'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/hulubul/channel_gateway/models/channel.py
from dataclasses import dataclass

from hulubul.core.models.domain.hulubul_models import Medium


@dataclass(frozen=True)
class ChannelRef:
    """The (medium, systemID) identity pair — a reference, not the full Channel entity.

    The full `Channel` entity (id, validationStatus, alias, telephone, email) is modeled in
    model/linkml/hulubul_channel.yaml and generated into
    hulubul.core.models.domain.hulubul_models. It is resolved downstream by
    resolve_channel_actor, never constructed here — its `id` is a graph node identity that
    only exists once the node is persisted.
    """

    medium: Medium
    system_id: str


def derive_session_id(medium: Medium, system_id: str) -> str:
    return f"{medium.value}:{system_id}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/unit/hulubul/channel_gateway/models/test_channel.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/hulubul/channel_gateway/models/channel.py tests/unit/hulubul/channel_gateway/models/test_channel.py
git commit -m "feat(channel-gateway): add ChannelRef value object and deterministic session_id derivation"
```

---

### Task 4: Adapters — `ChannelPort` interface

**Files:**
- Create: `src/hulubul/channel_gateway/adapters/channel_port.py`
- Test: `tests/unit/hulubul/channel_gateway/adapters/test_channel_port.py`

**Interfaces:**
- Consumes: `InboundMessage`, `TextMessage`, `MediaMessage` from Task 2.
- Produces: `ChannelPort` ABC with `receive(raw_update: object) -> InboundMessage` and `async send(system_id: str, message: TextMessage | MediaMessage) -> None` — implemented by Tasks 5 and 6.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/hulubul/channel_gateway/adapters/test_channel_port.py
import inspect

from hulubul.channel_gateway.adapters.channel_port import ChannelPort


def test_channel_port_cannot_be_instantiated_directly():
    assert inspect.isabstract(ChannelPort)


def test_channel_port_declares_receive_and_send():
    assert "receive" in ChannelPort.__abstractmethods__
    assert "send" in ChannelPort.__abstractmethods__


def test_a_conforming_subclass_can_be_instantiated():
    class FakeAdapter(ChannelPort):
        def receive(self, raw_update: object):
            raise NotImplementedError

        async def send(self, system_id: str, message) -> None:
            raise NotImplementedError

    FakeAdapter()  # does not raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/unit/hulubul/channel_gateway/adapters/test_channel_port.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hulubul.channel_gateway.adapters.channel_port'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/hulubul/channel_gateway/adapters/channel_port.py
from abc import ABC, abstractmethod

from hulubul.channel_gateway.models.message import (
    InboundMessage,
    MediaMessage,
    TextMessage,
)


class ChannelPort(ABC):
    @abstractmethod
    def receive(self, raw_update: object) -> InboundMessage:
        """Normalize a channel-specific raw update into an InboundMessage."""

    @abstractmethod
    async def send(self, system_id: str, message: TextMessage | MediaMessage) -> None:
        """Send an outbound message to the given channel-specific system_id."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/unit/hulubul/channel_gateway/adapters/test_channel_port.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/hulubul/channel_gateway/adapters/channel_port.py tests/unit/hulubul/channel_gateway/adapters/test_channel_port.py
git commit -m "feat(channel-gateway): add ChannelPort interface"
```

---

### Task 5: Adapters — `TelegramAdapter`

**Files:**
- Create: `src/hulubul/channel_gateway/adapters/telegram_adapter.py`
- Test: `tests/unit/hulubul/channel_gateway/adapters/test_telegram_adapter.py`

**Interfaces:**
- Consumes: `ChannelPort` (Task 4), `InboundMessage`/`Medium`/`TextMessage`/`MediaMessage` (Task 2), `aiogram.Bot`, `aiogram.types.Message`.
- Produces: `TelegramAdapter(bot: aiogram.Bot)` implementing `ChannelPort`, consumed by Task 8 (entrypoint) and Task 7 (relay service tests).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/hulubul/channel_gateway/adapters/test_telegram_adapter.py
from unittest.mock import AsyncMock, MagicMock

import pytest

from hulubul.core.models.domain.hulubul_models import Medium

from hulubul.channel_gateway.adapters.telegram_adapter import TelegramAdapter
from hulubul.channel_gateway.models.message import MediaMessage, TextMessage


def _fake_aiogram_message(text: str, chat_id: int, reply_to_message_id: int | None = None):
    message = MagicMock()
    message.text = text
    message.chat.id = chat_id
    message.reply_to_message = None
    if reply_to_message_id is not None:
        message.reply_to_message = MagicMock()
        message.reply_to_message.message_id = reply_to_message_id
    return message


def test_receive_normalizes_a_plain_text_update():
    adapter = TelegramAdapter(bot=MagicMock())
    raw = _fake_aiogram_message(text="hello", chat_id=123456789)

    inbound = adapter.receive(raw)

    assert inbound.medium is Medium.Telegram
    assert inbound.system_id == "123456789"
    assert inbound.text == "hello"
    assert inbound.reply_to_message_id is None


def test_receive_captures_reply_to_message_id_when_present():
    adapter = TelegramAdapter(bot=MagicMock())
    raw = _fake_aiogram_message(text="yes", chat_id=123456789, reply_to_message_id=555)

    inbound = adapter.receive(raw)

    assert inbound.reply_to_message_id == "555"


@pytest.mark.asyncio
async def test_send_text_message_calls_bot_send_message():
    bot = MagicMock()
    bot.send_message = AsyncMock()
    adapter = TelegramAdapter(bot=bot)

    await adapter.send("123456789", TextMessage(text="reply"))

    bot.send_message.assert_awaited_once_with(chat_id=123456789, text="reply")


@pytest.mark.asyncio
async def test_send_media_message_calls_bot_send_photo():
    bot = MagicMock()
    bot.send_photo = AsyncMock()
    adapter = TelegramAdapter(bot=bot)

    await adapter.send(
        "123456789", MediaMessage(url="https://example.com/a.jpg", caption="a parcel photo")
    )

    bot.send_photo.assert_awaited_once_with(
        chat_id=123456789, photo="https://example.com/a.jpg", caption="a parcel photo"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/unit/hulubul/channel_gateway/adapters/test_telegram_adapter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hulubul.channel_gateway.adapters.telegram_adapter'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/hulubul/channel_gateway/adapters/telegram_adapter.py
from aiogram import Bot

from hulubul.core.models.domain.hulubul_models import Medium

from hulubul.channel_gateway.adapters.channel_port import ChannelPort
from hulubul.channel_gateway.models.message import (
    InboundMessage,
    MediaMessage,
    TextMessage,
)


class TelegramAdapter(ChannelPort):
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    def receive(self, raw_update: object) -> InboundMessage:
        reply_to_message_id = None
        if getattr(raw_update, "reply_to_message", None) is not None:
            reply_to_message_id = str(raw_update.reply_to_message.message_id)
        return InboundMessage(
            medium=Medium.Telegram,
            system_id=str(raw_update.chat.id),
            text=raw_update.text,
            reply_to_message_id=reply_to_message_id,
        )

    async def send(self, system_id: str, message: TextMessage | MediaMessage) -> None:
        chat_id = int(system_id)
        if isinstance(message, TextMessage):
            await self._bot.send_message(chat_id=chat_id, text=message.text)
        else:
            await self._bot.send_photo(
                chat_id=chat_id, photo=message.url, caption=message.caption
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/unit/hulubul/channel_gateway/adapters/test_telegram_adapter.py -v`
Expected: PASS (4 tests)

Note: if `pytest-asyncio` is not yet a dev dependency, add it to the `test` group in `pyproject.toml` (`pytest-asyncio = "0.24.0"`) and add `asyncio_mode = "auto"` under `[tool.pytest.ini_options]` before running.

- [ ] **Step 5: Commit**

```bash
git add src/hulubul/channel_gateway/adapters/telegram_adapter.py tests/unit/hulubul/channel_gateway/adapters/test_telegram_adapter.py pyproject.toml
git commit -m "feat(channel-gateway): add TelegramAdapter implementing ChannelPort via aiogram"
```

---

### Task 6: Adapters — `WhatsAppAdapter` stub

**Files:**
- Create: `src/hulubul/channel_gateway/adapters/whatsapp_adapter.py`
- Test: `tests/unit/hulubul/channel_gateway/adapters/test_whatsapp_adapter.py`

**Interfaces:**
- Consumes: `ChannelPort` (Task 4).
- Produces: `WhatsAppAdapter()` implementing `ChannelPort`, both methods raising `NotImplementedError`. Not consumed by any other task in this plan — proves interface fit only.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/hulubul/channel_gateway/adapters/test_whatsapp_adapter.py
import pytest

from hulubul.channel_gateway.adapters.channel_port import ChannelPort
from hulubul.channel_gateway.adapters.whatsapp_adapter import WhatsAppAdapter
from hulubul.channel_gateway.models.message import TextMessage


def test_whatsapp_adapter_is_a_channel_port():
    adapter: ChannelPort = WhatsAppAdapter()
    assert isinstance(adapter, ChannelPort)


def test_receive_is_not_implemented():
    adapter = WhatsAppAdapter()
    with pytest.raises(NotImplementedError):
        adapter.receive(raw_update={"some": "360dialog payload"})


@pytest.mark.asyncio
async def test_send_is_not_implemented():
    adapter = WhatsAppAdapter()
    with pytest.raises(NotImplementedError):
        await adapter.send("+15551234567", TextMessage(text="hi"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/unit/hulubul/channel_gateway/adapters/test_whatsapp_adapter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hulubul.channel_gateway.adapters.whatsapp_adapter'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/hulubul/channel_gateway/adapters/whatsapp_adapter.py
from hulubul.channel_gateway.adapters.channel_port import ChannelPort
from hulubul.channel_gateway.models.message import (
    InboundMessage,
    MediaMessage,
    TextMessage,
)


class WhatsAppAdapter(ChannelPort):
    """Stub proving ChannelPort generalizes to WhatsApp/360dialog.

    Not wired to any live WhatsApp API. Implement receive()/send() only
    when a real 360dialog integration is scoped (see channel-gateway
    design.md non-goals).
    """

    def receive(self, raw_update: object) -> InboundMessage:
        raise NotImplementedError("WhatsApp adapter is a stub; not implemented yet.")

    async def send(self, system_id: str, message: TextMessage | MediaMessage) -> None:
        raise NotImplementedError("WhatsApp adapter is a stub; not implemented yet.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/unit/hulubul/channel_gateway/adapters/test_whatsapp_adapter.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Verify structural typing with mypy**

Run: `poetry run mypy src/hulubul/channel_gateway/adapters/whatsapp_adapter.py`
Expected: no errors (confirms `WhatsAppAdapter` satisfies `ChannelPort` per design.md D3's scenario "The stub type-checks against the shared interface").

- [ ] **Step 6: Commit**

```bash
git add src/hulubul/channel_gateway/adapters/whatsapp_adapter.py tests/unit/hulubul/channel_gateway/adapters/test_whatsapp_adapter.py
git commit -m "feat(channel-gateway): add WhatsAppAdapter stub proving ChannelPort fit"
```

---

### Task 7: Adapters — `LangflowClient`

**Files:**
- Create: `src/hulubul/channel_gateway/adapters/langflow_client.py`
- Test: `tests/unit/hulubul/channel_gateway/adapters/test_langflow_client.py`

**Interfaces:**
- Consumes: `httpx.AsyncClient`.
- Produces: `LangflowClient(base_url: str, flow_id: str, client: httpx.AsyncClient)` with
  `async def run(self, session_id: str, medium: str, system_id: str, text: str) -> str | None`
  (returns the reply text, or `None` on failure) — consumed by Task 8 (`relay_message`).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/hulubul/channel_gateway/adapters/test_langflow_client.py
import httpx
import pytest

from hulubul.channel_gateway.adapters.langflow_client import LangflowClient


@pytest.mark.asyncio
async def test_run_posts_session_id_and_channel_identity_and_returns_reply_text():
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["json"] = httpx.Request.read(request) and request.content
        captured_request["url"] = str(request.url)
        return httpx.Response(
            200,
            json={
                "outputs": [
                    {"outputs": [{"results": {"message": {"data": {"text": "Got it!"}}}}]}
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = LangflowClient(
            base_url="http://langflow:7860", flow_id="abc123", client=http_client
        )
        reply = await client.run(
            session_id="Telegram:123", medium="Telegram", system_id="123", text="hello"
        )

    assert reply == "Got it!"
    assert captured_request["url"] == "http://langflow:7860/api/v1/run/abc123"


@pytest.mark.asyncio
async def test_run_returns_none_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = LangflowClient(
            base_url="http://langflow:7860", flow_id="abc123", client=http_client
        )
        reply = await client.run(
            session_id="Telegram:123", medium="Telegram", system_id="123", text="hello"
        )

    assert reply is None


@pytest.mark.asyncio
async def test_run_returns_none_on_unexpected_response_shape():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = LangflowClient(
            base_url="http://langflow:7860", flow_id="abc123", client=http_client
        )
        reply = await client.run(
            session_id="Telegram:123", medium="Telegram", system_id="123", text="hello"
        )

    assert reply is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/unit/hulubul/channel_gateway/adapters/test_langflow_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hulubul.channel_gateway.adapters.langflow_client'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/hulubul/channel_gateway/adapters/langflow_client.py
import logging

import httpx

logger = logging.getLogger(__name__)


class LangflowClient:
    def __init__(self, base_url: str, flow_id: str, client: httpx.AsyncClient) -> None:
        self._base_url = base_url.rstrip("/")
        self._flow_id = flow_id
        self._client = client

    async def run(
        self, session_id: str, medium: str, system_id: str, text: str
    ) -> str | None:
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
            return data["outputs"][0]["outputs"][0]["results"]["message"]["data"]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning("Unexpected LangFlow response shape: %s", exc)
            return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/unit/hulubul/channel_gateway/adapters/test_langflow_client.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/hulubul/channel_gateway/adapters/langflow_client.py tests/unit/hulubul/channel_gateway/adapters/test_langflow_client.py
git commit -m "feat(channel-gateway): add LangflowClient adapter wrapping the Run API"
```

---

### Task 8: Services — `relay_message`

**Files:**
- Create: `src/hulubul/channel_gateway/services/relay_message.py`
- Test: `tests/unit/hulubul/channel_gateway/services/test_relay_message.py`

**Interfaces:**
- Consumes: `ChannelPort`, `LangflowClient`, `derive_session_id`, `InboundMessage`, `TextMessage`.
- Produces: `async def relay_inbound_message(adapter: ChannelPort, langflow_client: LangflowClient, raw_update: object) -> None` — consumed by Task 9 (entrypoint).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/hulubul/channel_gateway/services/test_relay_message.py
from unittest.mock import AsyncMock, MagicMock

import pytest

from hulubul.core.models.domain.hulubul_models import Medium

from hulubul.channel_gateway.models.message import InboundMessage, TextMessage
from hulubul.channel_gateway.services.relay_message import relay_inbound_message


@pytest.mark.asyncio
async def test_relay_calls_langflow_with_derived_session_id_and_sends_reply_to_origin():
    adapter = MagicMock()
    adapter.receive.return_value = InboundMessage(
        medium=Medium.Telegram, system_id="123456789", text="I need to send a parcel"
    )
    adapter.send = AsyncMock()

    langflow_client = MagicMock()
    langflow_client.run = AsyncMock(return_value="Sure, where is it going?")

    await relay_inbound_message(adapter, langflow_client, raw_update=object())

    langflow_client.run.assert_awaited_once_with(
        session_id="Telegram:123456789",
        medium="Telegram",
        system_id="123456789",
        text="I need to send a parcel",
    )
    adapter.send.assert_awaited_once_with(
        "123456789", TextMessage(text="Sure, where is it going?")
    )


@pytest.mark.asyncio
async def test_relay_does_not_send_when_langflow_call_fails():
    adapter = MagicMock()
    adapter.receive.return_value = InboundMessage(
        medium=Medium.Telegram, system_id="123456789", text="hi"
    )
    adapter.send = AsyncMock()

    langflow_client = MagicMock()
    langflow_client.run = AsyncMock(return_value=None)

    await relay_inbound_message(adapter, langflow_client, raw_update=object())

    adapter.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_relay_does_not_crash_the_process_when_send_fails():
    adapter = MagicMock()
    adapter.receive.return_value = InboundMessage(
        medium=Medium.Telegram, system_id="123456789", text="hi"
    )
    adapter.send = AsyncMock(side_effect=RuntimeError("Telegram API: bot was blocked by the user"))

    langflow_client = MagicMock()
    langflow_client.run = AsyncMock(return_value="Sure, where is it going?")

    # Must not raise — a delivery failure for one message must not take down
    # the long-running gateway process for every subsequent message.
    await relay_inbound_message(adapter, langflow_client, raw_update=object())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/unit/hulubul/channel_gateway/services/test_relay_message.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hulubul.channel_gateway.services.relay_message'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/hulubul/channel_gateway/services/relay_message.py
import logging

from hulubul.channel_gateway.adapters.channel_port import ChannelPort
from hulubul.channel_gateway.adapters.langflow_client import LangflowClient
from hulubul.channel_gateway.models.channel import derive_session_id
from hulubul.channel_gateway.models.message import TextMessage

logger = logging.getLogger(__name__)


async def relay_inbound_message(
    adapter: ChannelPort, langflow_client: LangflowClient, raw_update: object
) -> None:
    inbound = adapter.receive(raw_update)
    session_id = derive_session_id(inbound.medium, inbound.system_id)

    reply_text = await langflow_client.run(
        session_id=session_id,
        medium=inbound.medium.value,
        system_id=inbound.system_id,
        text=inbound.text,
    )

    if reply_text is None:
        logger.warning(
            "No reply from LangFlow for session_id=%s; not sending a response.", session_id
        )
        return

    try:
        await adapter.send(inbound.system_id, TextMessage(text=reply_text))
    except Exception:
        logger.exception(
            "Failed to send reply for session_id=%s; message is dropped, not retried.",
            session_id,
        )
```

Error-handling policy lives here (`services/`), not in the adapter — `TelegramAdapter.send()`
itself is left to raise naturally on a Telegram API failure (e.g. bot blocked by the user);
this is where that's caught so it never crashes the long-running `entrypoints/telegram_bot.py`
process. See design.md's Error Handling Matrix.

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/unit/hulubul/channel_gateway/services/test_relay_message.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/hulubul/channel_gateway/services/relay_message.py tests/unit/hulubul/channel_gateway/services/test_relay_message.py
git commit -m "feat(channel-gateway): add relay_message service orchestrating adapter <-> LangFlow"
```

---

### Task 9: Entrypoint — `telegram_bot.py`

**Files:**
- Create: `src/hulubul/channel_gateway/entrypoints/telegram_bot.py`
- Test: `tests/unit/hulubul/channel_gateway/entrypoints/test_telegram_bot.py`

**Interfaces:**
- Consumes: `TelegramAdapter` (Task 5), `LangflowClient` (Task 7), `relay_inbound_message` (Task 8).
- Produces: `load_config() -> GatewayConfig` (reads `TELEGRAM_BOT_TOKEN`, `LANGFLOW_API_URL`, `LANGFLOW_FLOW_ID`, `GATEWAY_MODE` from `os.environ`) and `async def main() -> None` — the process entrypoint, not consumed elsewhere (top of the dependency graph).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/hulubul/channel_gateway/entrypoints/test_telegram_bot.py
import pytest

from hulubul.channel_gateway.entrypoints.telegram_bot import GatewayConfig, load_config


def test_load_config_reads_required_environment_variables(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("LANGFLOW_API_URL", "http://langflow:7860")
    monkeypatch.setenv("LANGFLOW_FLOW_ID", "flow-1")
    monkeypatch.setenv("GATEWAY_MODE", "polling")

    config = load_config()

    assert config == GatewayConfig(
        telegram_bot_token="123:abc",
        langflow_api_url="http://langflow:7860",
        langflow_flow_id="flow-1",
        mode="polling",
    )


def test_load_config_raises_when_a_required_variable_is_missing(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("LANGFLOW_API_URL", "http://langflow:7860")
    monkeypatch.setenv("LANGFLOW_FLOW_ID", "flow-1")
    monkeypatch.setenv("GATEWAY_MODE", "polling")

    with pytest.raises(KeyError):
        load_config()


def test_load_config_rejects_an_unknown_gateway_mode(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("LANGFLOW_API_URL", "http://langflow:7860")
    monkeypatch.setenv("LANGFLOW_FLOW_ID", "flow-1")
    monkeypatch.setenv("GATEWAY_MODE", "carrier-pigeon")

    with pytest.raises(ValueError, match="GATEWAY_MODE"):
        load_config()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/unit/hulubul/channel_gateway/entrypoints/test_telegram_bot.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hulubul.channel_gateway.entrypoints.telegram_bot'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/hulubul/channel_gateway/entrypoints/telegram_bot.py
import os
from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.types import Message
import httpx

from hulubul.channel_gateway.adapters.langflow_client import LangflowClient
from hulubul.channel_gateway.adapters.telegram_adapter import TelegramAdapter
from hulubul.channel_gateway.services.relay_message import relay_inbound_message

_VALID_MODES = {"polling", "webhook"}


@dataclass(frozen=True)
class GatewayConfig:
    telegram_bot_token: str
    langflow_api_url: str
    langflow_flow_id: str
    mode: str


def load_config() -> GatewayConfig:
    mode = os.environ["GATEWAY_MODE"]
    if mode not in _VALID_MODES:
        raise ValueError(f"GATEWAY_MODE must be one of {_VALID_MODES}, got {mode!r}")
    return GatewayConfig(
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        langflow_api_url=os.environ["LANGFLOW_API_URL"],
        langflow_flow_id=os.environ["LANGFLOW_FLOW_ID"],
        mode=mode,
    )


async def main() -> None:
    config = load_config()
    bot = Bot(token=config.telegram_bot_token)
    dispatcher = Dispatcher()
    adapter = TelegramAdapter(bot=bot)

    async with httpx.AsyncClient() as http_client:
        langflow_client = LangflowClient(
            base_url=config.langflow_api_url,
            flow_id=config.langflow_flow_id,
            client=http_client,
        )

        @dispatcher.message()
        async def on_message(message: Message) -> None:
            await relay_inbound_message(adapter, langflow_client, message)

        if config.mode == "polling":
            await dispatcher.start_polling(bot)
        else:
            # Webhook mode: registration and the aiohttp server are wired in
            # Task 11 (local deployment), where the public URL (via ngrok
            # locally) is known at container startup.
            raise NotImplementedError(
                "Webhook server wiring is completed in the local-deployment task."
            )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/unit/hulubul/channel_gateway/entrypoints/test_telegram_bot.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/hulubul/channel_gateway/entrypoints/telegram_bot.py tests/unit/hulubul/channel_gateway/entrypoints/test_telegram_bot.py
git commit -m "feat(channel-gateway): add telegram_bot entrypoint with config loading and polling wiring"
```

---

### Task 10: Architecture documentation

**Files:**
- Create: `architecture/channel-gateway-blueprint.md`
- Create: `architecture/channel-gateway-runbook.md`
- Modify: `architecture/README.md`

**Interfaces:** None (documentation only, no code).

Both docs are prose deliverables, not code — apply the `meaningfy-core:technical-writing`
skill (clarity check, AsciiDoc/Markdown conventions) while drafting them, not just a literal
transcription of design.md. Each section below names its exact source in this change's own
artifacts — an executor with no memory of this change's brainstorm should still be able to
write accurate prose from these pointers alone, but the *quality* of the prose (structure,
what to lead with, what to cut) is the technical-writing skill's job, not something this plan
does for you.

- [ ] **Step 1: Write `architecture/channel-gateway-blueprint.md`**

Section-by-section source material (write in this order):
1. **Context** — design.md's `## Context` section verbatim as source (Phase 3 positioning,
   why this is being pulled forward ahead of Phase 1 completion).
2. **Architecture overview** — the ASCII diagram from `brainstorm.md`'s "Q1–Q8" section
   (Telegram → gateway process → LangFlow → reply), redrawn as a proper Mermaid diagram per
   the `architecture` skill's C4/diagram conventions, not left as ASCII in a permanent doc.
3. **Decisions D1–D3, D5–D9** — one subsection per decision, each stating the choice,
   rationale, and rejected alternative from design.md (D4 gets its own subsection below
   instead, since it needs more room).
4. **Session/identity handling** — D4 in full, plus the `ChannelRef`-vs-`Channel` distinction
   from D7's "Post-brainstorm correction" note (the `id`-field/persistence-timing argument,
   not just the naming rationale) — this is the part most likely to be re-litigated later, so
   it needs the actual reasoning present, not just the conclusion.
5. **Module layout** — the file tree from D7's Choice block, with each path's one-line role.
6. **Deployment topology** — D5 (container topology) + D6 (polling/webhook modes), forward
   reference to the runbook for the actual how-to.
7. **Known limitations** — copy design.md's `## Risks / Trade-offs` and `## Open Questions`
   sections in full; do not summarize or drop entries.

- [ ] **Step 2: Write `architecture/channel-gateway-runbook.md`**

Section-by-section source material:
1. **Telegram bot setup** — creating a bot via @BotFather, obtaining the token, setting the
   webhook `secret_token`, disabling bot privacy mode — per `gateway-deployment-setup` spec
   "Telegram bot configuration is documented end-to-end"; write this as a numbered,
   copy-pasteable sequence a developer with zero prior Telegram bot experience can follow
   start to finish (the spec's own acceptance scenario is exactly this test).
2. **Local Compose bring-up** — `make up`, then `GATEWAY_MODE=polling` first bring-up per
   design.md's Migration Plan, then switching to `GATEWAY_MODE=webhook` with the `ngrok`
   Compose profile (Task 11, Steps 6–7's exact commands).
3. **WhatsApp configuration** — explicitly marked "not yet implemented" with a link back to
   the blueprint doc's Non-Goals, not left silently absent (a reader searching for WhatsApp
   setup should find this section and understand why it's empty, not conclude the doc is
   incomplete).
4. **Running the test suites locally** — unit/feature commands from Task 14 Step 3, plus the
   e2e instructions filled in by Task 13 Step 3 (`TELEGRAM_TEST_BOT_TOKEN`,
   `TELEGRAM_TEST_CHAT_ID`, the exact `pytest tests/e2e/` invocation).

- [ ] **Step 3: Cross-link from `architecture/README.md`**

Add a row/entry pointing to both new docs, noting this pulls forward Phase 3 §6 scope ahead
of the active Phase 1 change, per design.md Context.

- [ ] **Step 4: Commit**

```bash
git add architecture/channel-gateway-blueprint.md architecture/channel-gateway-runbook.md architecture/README.md
git commit -m "docs(architecture): add channel gateway blueprint and runbook"
```

---

### Task 11: Local deployment — Dockerfile, Compose services, webhook wiring

**Files:**
- Create: `infra/channel-gateway/Dockerfile`
- Modify: `infra/docker-compose.yaml`
- Modify: `infra/.env.example`
- Modify: `src/hulubul/channel_gateway/entrypoints/telegram_bot.py` (complete webhook mode, replacing the `NotImplementedError` from Task 9)

**Interfaces:**
- Consumes: `GatewayConfig`, `main()` from Task 9.
- Produces: a running `channel-gateway` container reachable via `docker compose up`.

- [ ] **Step 1: Write `infra/channel-gateway/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry==1.8.3

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main,gateway --no-interaction --no-ansi --no-root

COPY src/ src/

CMD ["python", "-m", "hulubul.channel_gateway.entrypoints.telegram_bot"]
```

- [ ] **Step 2: Add the `channel-gateway` service to `infra/docker-compose.yaml`**

Add after the existing `langflow` service block:

```yaml
  channel-gateway:
    build: ../
    dockerfile: infra/channel-gateway/Dockerfile

    depends_on:
      langflow:
        condition: service_started

    environment:
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      LANGFLOW_API_URL: http://langflow:7860
      LANGFLOW_FLOW_ID: ${LANGFLOW_FLOW_ID}
      GATEWAY_MODE: ${GATEWAY_MODE:-polling}
      TELEGRAM_WEBHOOK_SECRET: ${TELEGRAM_WEBHOOK_SECRET:-}
      NGROK_API_URL: http://ngrok:4040
```

- [ ] **Step 3: Add the `ngrok` service, gated to webhook mode via a Compose profile**

```yaml
  ngrok:
    image: ngrok/ngrok:3
    command: ["http", "channel-gateway:8080"]
    environment:
      NGROK_AUTHTOKEN: ${NGROK_AUTHTOKEN}
    ports:
      - "4040:4040"
    profiles: ["webhook"]
```

- [ ] **Step 4: Update `infra/.env.example`**

Add:
```
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=
LANGFLOW_FLOW_ID=
GATEWAY_MODE=polling
NGROK_AUTHTOKEN=
```

- [ ] **Step 5: Complete webhook mode in `telegram_bot.py`**

Replace the `NotImplementedError` branch from Task 9 with an aiohttp webhook server that
looks up the current ngrok public URL and registers it with Telegram on startup:

```python
        else:
            import httpx as _httpx
            from aiogram.webhook.aiohttp_server import (
                SimpleRequestHandler,
                setup_application,
            )
            from aiohttp import web

            async with _httpx.AsyncClient() as ngrok_client:
                tunnels_resp = await ngrok_client.get(
                    f"{os.environ.get('NGROK_API_URL', 'http://ngrok:4040')}/api/tunnels"
                )
                public_url = tunnels_resp.json()["tunnels"][0]["public_url"]

            secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET") or None
            await bot.set_webhook(
                url=f"{public_url}/webhook", secret_token=secret, drop_pending_updates=True
            )

            app = web.Application()
            SimpleRequestHandler(dispatcher=dispatcher, bot=bot, secret_token=secret).register(
                app, path="/webhook"
            )
            setup_application(app, dispatcher, bot=bot)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host="0.0.0.0", port=8080)
            await site.start()
            await asyncio.Event().wait()
```

Add `expose: ["8080"]` under the `channel-gateway` service block from Step 2 so `ngrok` can
reach it.

- [ ] **Step 6: Verify local bring-up in polling mode**

Run: `cd infra && docker compose up -d --build channel-gateway`
Expected: container starts and logs "Start polling" (aiogram's standard startup log line),
no crash loop (`docker compose ps` shows `channel-gateway` as `running`).

- [ ] **Step 7: Verify local bring-up in webhook mode**

Run: `cd infra && GATEWAY_MODE=webhook docker compose --profile webhook up -d --build channel-gateway ngrok`
Expected: `channel-gateway` logs show the registered ngrok public URL; sending a message to
the real test bot results in a reply (manual check against a real Telegram bot token from
the runbook's @BotFather setup).

- [ ] **Step 8: Commit**

```bash
git add infra/channel-gateway/Dockerfile infra/docker-compose.yaml infra/.env.example src/hulubul/channel_gateway/entrypoints/telegram_bot.py
git commit -m "feat(channel-gateway): add local Docker Compose deployment with polling and ngrok webhook modes"
```

---

### Task 12: Feature tests (Gherkin, LangFlow-connected)

**Files:**
- Create: `tests/features/telegram_message_relay.feature`
- Create: `tests/feature/__init__.py`
- Create: `tests/feature/test_telegram_message_relay.py`

**Interfaces:**
- Consumes: `relay_inbound_message` (Task 8), `LangflowClient` (Task 7), a real local LangFlow
  container (via `infra/docker-compose.yaml`, already running from Task 11).

- [ ] **Step 1: Write the Gherkin feature file**

```gherkin
# tests/features/telegram_message_relay.feature
Feature: Telegram message relay to LangFlow
  As a Sender messaging Hulubul on Telegram
  I want my message routed to the request-intake flow
  So that I can start a delivery request by chatting normally

  Scenario Outline: A first message from a new Telegram channel reaches LangFlow
    Given a Telegram chat with system_id "<system_id>" that has never messaged Hulubul before
    When the sender sends the message "<message_text>"
    Then LangFlow receives session_id "<expected_session_id>"
    And LangFlow receives the channel identity medium "Telegram" and system_id "<system_id>"

    Examples:
      | system_id   | message_text                  | expected_session_id |
      | 111111111   | I need to send a parcel       | Telegram:111111111  |
      | 222222222   | Hi, can you help me ship this | Telegram:222222222  |

  Scenario: A reply from LangFlow is sent back to the originating chat
    Given a Telegram chat with system_id "333333333"
    And LangFlow will reply with "Sure, where is it going?"
    When the sender sends the message "I need to send a parcel"
    Then the sender receives the message "Sure, where is it going?"
```

- [ ] **Step 2: Run the feature file to verify it fails (no step definitions yet)**

Run: `poetry run pytest tests/feature/ -v`
Expected: FAIL/ERROR — `tests/feature/test_telegram_message_relay.py` does not exist yet, so
pytest-bdd has no step definitions bound to the `.feature` file.

- [ ] **Step 3: Write the step definitions**

```python
# tests/feature/test_telegram_message_relay.py
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from hulubul.core.models.domain.hulubul_models import Medium

from hulubul.channel_gateway.models.message import InboundMessage, TextMessage
from hulubul.channel_gateway.services.relay_message import relay_inbound_message

scenarios("../features/telegram_message_relay.feature")


@pytest.fixture
def context():
    return {}


@given(parsers.parse('a Telegram chat with system_id "{system_id}" that has never messaged Hulubul before'))
@given(parsers.parse('a Telegram chat with system_id "{system_id}"'))
def a_telegram_chat(context, system_id):
    context["system_id"] = system_id
    context["adapter"] = MagicMock()
    context["adapter"].send = AsyncMock()
    context["langflow_client"] = MagicMock()
    context["langflow_client"].run = AsyncMock(return_value="")


@given(parsers.parse('LangFlow will reply with "{reply_text}"'))
def langflow_will_reply(context, reply_text):
    context["langflow_client"].run = AsyncMock(return_value=reply_text)


@when(parsers.parse('the sender sends the message "{message_text}"'))
@pytest.mark.asyncio
async def sender_sends_message(context, message_text):
    context["adapter"].receive.return_value = InboundMessage(
        medium=Medium.Telegram, system_id=context["system_id"], text=message_text
    )
    await relay_inbound_message(context["adapter"], context["langflow_client"], raw_update=object())


@then(parsers.parse('LangFlow receives session_id "{expected_session_id}"'))
def langflow_receives_session_id(context, expected_session_id):
    _, kwargs = context["langflow_client"].run.await_args
    assert kwargs["session_id"] == expected_session_id


@then(parsers.parse('LangFlow receives the channel identity medium "{medium}" and system_id "{system_id}"'))
def langflow_receives_channel_identity(context, medium, system_id):
    _, kwargs = context["langflow_client"].run.await_args
    assert kwargs["medium"] == medium
    assert kwargs["system_id"] == system_id


@then(parsers.parse('the sender receives the message "{reply_text}"'))
def sender_receives_message(context, reply_text):
    context["adapter"].send.assert_awaited_once_with(
        context["system_id"], TextMessage(text=reply_text)
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/feature/ -v`
Expected: PASS (3 scenarios: 2 from the Scenario Outline + 1 from the reply scenario)

Note: this suite currently exercises `relay_inbound_message` with a mocked `LangflowClient`
rather than a live LangFlow container, matching design.md D8's "synthetic inbound" framing —
if/when the suite is upgraded to call a real local LangFlow instance (per
`gateway-deployment-setup` spec), replace the `langflow_client` fixture with a real
`LangflowClient` pointed at `http://localhost:7860` and gate the suite on the compose stack
being up.

- [ ] **Step 5: Commit**

```bash
git add tests/features/telegram_message_relay.feature tests/feature/
git commit -m "test(channel-gateway): add BDD feature tests for Telegram message relay"
```

---

### Task 13: e2e tests (local/manual only, excluded from CI)

**Files:**
- Create: `tests/e2e/__init__.py`
- Create: `tests/e2e/test_telegram_roundtrip.py`
- Create: `tests/e2e/test_telegram_adapter_isolation.py`
- Modify: `architecture/channel-gateway-runbook.md` (fill in the e2e run instructions placeholder from Task 10)

**Interfaces:**
- Consumes: a real Telegram test bot (token from local `.env`, per the runbook), the real
  local LangFlow stack (Task 11).

- [ ] **Step 1: Write the full-roundtrip e2e test**

```python
# tests/e2e/test_telegram_roundtrip.py
"""
Manual/local-only: requires a real Telegram test bot and the local LangFlow
stack running (`docker compose up`). Not run in CI.

Run with: poetry run pytest tests/e2e/test_telegram_roundtrip.py -v -s
Requires: TELEGRAM_TEST_BOT_TOKEN and TELEGRAM_TEST_CHAT_ID in the environment
(see architecture/channel-gateway-runbook.md "Running e2e tests locally").
"""

import os

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("TELEGRAM_TEST_BOT_TOKEN"),
    reason="requires a real Telegram test bot token; see channel-gateway-runbook.md",
)


@pytest.mark.asyncio
async def test_a_real_message_gets_a_real_reply():
    token = os.environ["TELEGRAM_TEST_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_TEST_CHAT_ID"]

    async with httpx.AsyncClient() as client:
        send_resp = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": "e2e: I need to send a parcel"},
        )
        assert send_resp.status_code == 200

        # The running channel-gateway container (polling mode) picks this up
        # and relays it to the local LangFlow stack; poll for the bot's reply.
        import asyncio

        for _ in range(10):
            await asyncio.sleep(2)
            updates_resp = await client.get(
                f"https://api.telegram.org/bot{token}/getUpdates", params={"offset": -1}
            )
            updates = updates_resp.json()["result"]
            if updates and updates[-1]["message"]["chat"]["id"] == int(chat_id):
                assert updates[-1]["message"]["text"]
                return
        pytest.fail("No reply received from the gateway within the polling window")
```

- [ ] **Step 2: Write the Telegram-adapter-isolation e2e test**

```python
# tests/e2e/test_telegram_adapter_isolation.py
"""
Manual/local-only: real Telegram test bot, LangFlow response stubbed via the
gateway's own mock mode. Isolates the Telegram send/receive contract from
LangFlow's behavior. Not run in CI.
"""

import os

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("TELEGRAM_TEST_BOT_TOKEN"),
    reason="requires a real Telegram test bot token; see channel-gateway-runbook.md",
)


@pytest.mark.asyncio
async def test_adapter_normalizes_and_sends_without_a_real_langflow_call(monkeypatch):
    # Point LANGFLOW_API_URL at a local stub server returning a fixed reply,
    # so this test exercises only the TelegramAdapter <-> Telegram contract.
    # See channel-gateway-runbook.md "e2e: isolating the Telegram adapter"
    # for how to start the stub server before running this test.
    token = os.environ["TELEGRAM_TEST_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_TEST_CHAT_ID"]

    async with httpx.AsyncClient() as client:
        send_resp = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": "e2e: adapter isolation ping"},
        )
        assert send_resp.status_code == 200
```

- [ ] **Step 3: Fill in the runbook's e2e instructions**

Replace the placeholder cross-reference from Task 10, Step 2 with concrete steps: how to
create a second (test) Telegram bot via @BotFather distinct from the dev bot, how to find
`TELEGRAM_TEST_CHAT_ID` (message the test bot once, call `getUpdates`), and the exact
`poetry run pytest tests/e2e/ -v -s` invocation with required environment variables.

- [ ] **Step 4: Verify CI does not pick up `tests/e2e/`**

Run: `grep -r "tests/e2e" .github/workflows/`
Expected: no match yet — confirms Task 14 (CI wiring) is what explicitly excludes it, not an
accidental default; run `poetry run pytest --collect-only` locally without `tests/e2e/`
excluded and confirm the e2e tests are skipped by default only because they require a live
bot token (`pytestmark`), not because pytest ignores the directory — CI wiring in Task 14
must add an explicit `--ignore=tests/e2e` for defense in depth.

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/ architecture/channel-gateway-runbook.md
git commit -m "test(channel-gateway): add e2e roundtrip and adapter-isolation tests (local/manual only)"
```

---

### Task 14: CI wiring and final verification

**Files:**
- Modify: `.github/workflows/ci.yaml`
- Modify: `Makefile` (if a `make test-gateway` or similar target is the repo's convention — check existing targets first)

**Interfaces:** None (CI configuration only).

- [ ] **Step 1: Update CI to install the `gateway` group and run unit + feature suites**

In `.github/workflows/ci.yaml`, find the step that runs `poetry install` and add `gateway` to
its `--with` groups, and find (or add) the test-execution step to explicitly exclude
`tests/e2e/`:

```yaml
      - name: Install dependencies
        run: poetry install --with test,quality,integration,langflow,gateway

      - name: Run unit and feature tests
        run: poetry run pytest tests/unit tests/feature --cov --ignore=tests/e2e -v
```

- [ ] **Step 2: Run the architecture check**

Run: `poetry run lint-imports`
Expected: PASS — confirms the `channel_gateway` layering contract from Task 1 holds across
all seven implementation tasks (2 through 9 wrote real code inside the layers).

- [ ] **Step 3: Run the full unit + feature suite locally with coverage**

Run: `poetry run pytest tests/unit/hulubul/channel_gateway tests/feature --cov=hulubul.channel_gateway --cov-report=term-missing -v`
Expected: PASS, coverage on `src/hulubul/channel_gateway/` ≥80% (per Global Constraints).

- [ ] **Step 4: Run mypy and ruff on the new package**

Run: `poetry run mypy src/hulubul/channel_gateway && poetry run ruff check src/hulubul/channel_gateway`
Expected: no errors.

- [ ] **Step 5: Manual verification against a real Telegram bot**

Follow `architecture/channel-gateway-runbook.md` end-to-end with a fresh @BotFather bot:
confirm polling mode replies to a real message, then switch to `GATEWAY_MODE=webhook` with
the `ngrok` profile and confirm the same, per design.md's Migration Plan.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/ci.yaml
git commit -m "ci(channel-gateway): run unit and feature suites, exclude e2e from CI"
```

- [ ] **Step 7: Dispatch code review as a separate pass**

Per `AGENTS.md`'s "Implementation subagent routing": *"Keep specification-conformance and
code-quality review as separate dispatches; the implementation subagent must not review its
own work."* Whatever implemented Tasks 0–14 MUST NOT review its own diff. The controller
dispatches a fresh review pass — `meaningfy-building:meaningfy-code-review` (or the
`meaningfy-building:code-reviewer` agent, or `/code-review` for the standalone read-only run)
— against the full branch diff, checking:
- Every requirement in `specs/channel-gateway-adapter/spec.md`,
  `specs/langflow-message-relay/spec.md`, `specs/gateway-deployment-setup/spec.md`, and
  `specs/domain-model-reachability/spec.md` has a corresponding passing test (spec
  conformance).
- Cosmic-python layering holds (`adapters/` depends only on `models/`; `services/` never
  imports `entrypoints/`) — cross-check against `poetry run lint-imports`'s actual output,
  not just that it exits zero.
- No new duplication of a LinkML-generated domain concept (the failure mode D7/D9 exist to
  prevent) was introduced elsewhere in the diff.

Only after this separate review pass is clean does the controller consider Tasks 0–14 done.
This step has no code of its own — it's a process gate, not an implementation step.
