"""Which contracts may terminate a flow.

A result boundary validates the value on its inbound edge and, until now,
accepted anything that parsed as one of the eleven registered contracts. That
answers "is this a known contract?" but never "is this the right contract for
this turn?" -- so a flow could end on a payload that is well-formed and still
wrong for the step that produced it.

Two rules close that gap.

**Allow-list.** A boundary declares the kinds that may legitimately terminate
it. LF-00 answers a sender with an intake outcome, a routing decision or an
error; a ``DataOperationResult`` arriving there is a symptom, not an answer.

**Hand-off rule.** A ``RouterResult`` says what *should* happen next. When it
routes to a specialist, the turn is not finished -- the specialist's result is
the answer. A ``RouterResult`` with ``target: intake`` arriving at a terminal
boundary therefore means the router decided to delegate and then didn't, which
otherwise renders as a perfectly ordinary "routing to intake" and looks
identical to success. This rule is what makes that failure visible.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Final

from hulubul.core.models.operational import ContractKind, RouterTarget

__all__ = [
    "DELEGATING_ROUTER_TARGETS",
    "TARGET_KEY",
    "is_terminal_contract",
    "parse_terminal_kinds",
    "terminal_rejection_reason",
]

TARGET_KEY: Final = "target"

#: Router targets that name a specialist flow. A ``RouterResult`` carrying one
#: is a hand-off; the specialist's own result is what terminates the turn.
DELEGATING_ROUTER_TARGETS: Final[frozenset[str]] = frozenset({RouterTarget.INTAKE.value})


def parse_terminal_kinds(declared: Iterable[str] | None) -> frozenset[ContractKind]:
    """Resolve a boundary's declared allow-list.

    An empty or absent declaration means "no allow-list" -- every registered
    kind stays acceptable, so a boundary that has not opted in behaves exactly
    as it did before.

    Unrecognized names are ignored rather than raising: this is read from flow
    JSON a human may have edited, and a typo there must not take a whole flow
    down at build time. A typo narrows nothing, so the boundary stays at least
    as permissive as its author intended -- never less.
    """
    if not declared:
        return frozenset(ContractKind)

    known = {kind.value: kind for kind in ContractKind}
    resolved = {known[name] for name in declared if name in known}
    return frozenset(resolved) if resolved else frozenset(ContractKind)


def is_terminal_contract(
    kind: ContractKind,
    payload: Mapping[str, Any],
    allowed: frozenset[ContractKind],
) -> bool:
    """Whether this contract may end the flow it arrived at."""
    if kind not in allowed:
        return False
    if kind is ContractKind.ROUTER_RESULT:
        return payload.get(TARGET_KEY) not in DELEGATING_ROUTER_TARGETS
    return True


def terminal_rejection_reason(
    kind: ContractKind,
    payload: Mapping[str, Any],
    allowed: frozenset[ContractKind],
) -> str | None:
    """Explain a rejection for logs, or ``None`` when the contract is terminal.

    Kept separate from :func:`is_terminal_contract` so the decision stays a
    plain predicate, and so the boundary can report *why* it refused without
    leaking the payload into a user-facing message.
    """
    if kind not in allowed:
        return f"{kind.value} is not an accepted terminal contract here"
    if kind is ContractKind.ROUTER_RESULT and payload.get(TARGET_KEY) in DELEGATING_ROUTER_TARGETS:
        return (
            f"router delegated to {payload.get(TARGET_KEY)!r} but no specialist "
            "result came back; the turn is unfinished"
        )
    return None
