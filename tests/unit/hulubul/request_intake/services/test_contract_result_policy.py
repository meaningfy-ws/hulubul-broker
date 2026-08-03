"""Tests for the terminal-contract policy."""

from typing import Any

import pytest

from hulubul.core.models.operational import ContractKind
from hulubul.request_intake.services.contract_result_policy import (
    is_terminal_contract,
    parse_terminal_kinds,
    terminal_rejection_reason,
)

ALL_KINDS = frozenset(ContractKind)
LF00_TERMINAL = frozenset(
    {ContractKind.INTAKE_RESULT, ContractKind.ROUTER_RESULT, ContractKind.OPERATIONAL_ERROR}
)


def _router(target: str) -> dict[str, Any]:
    return {"outcome": "routed", "target": target, "reason": "noBinding"}


class TestParseTerminalKinds:
    """A boundary that has not opted in must behave exactly as before."""

    @pytest.mark.parametrize("declared", [None, [], ()])
    def test_absent_declaration_allows_every_kind(self, declared: Any) -> None:
        assert parse_terminal_kinds(declared) == ALL_KINDS

    def test_declared_names_resolve_to_kinds(self) -> None:
        assert parse_terminal_kinds(["intake-result", "router-result"]) == {
            ContractKind.INTAKE_RESULT,
            ContractKind.ROUTER_RESULT,
        }

    def test_unknown_names_are_ignored_not_raised(self) -> None:
        """This is read from hand-editable flow JSON; a typo must not break the build."""
        assert parse_terminal_kinds(["intake-result", "nonsenseKind"]) == {
            ContractKind.INTAKE_RESULT
        }

    def test_all_names_unknown_falls_back_to_permissive(self) -> None:
        """A typo may never narrow the boundary below what its author declared."""
        assert parse_terminal_kinds(["nonsenseKind"]) == ALL_KINDS


class TestIsTerminalContract:
    """Which contracts may end a flow."""

    def test_declared_kind_is_terminal(self) -> None:
        assert is_terminal_contract(ContractKind.INTAKE_RESULT, {}, LF00_TERMINAL)

    def test_undeclared_kind_is_not(self) -> None:
        """The pre-existing hole: any of the eleven used to be accepted anywhere."""
        assert not is_terminal_contract(ContractKind.DATA_OPERATION_RESULT, {}, LF00_TERMINAL)

    def test_router_result_that_answers_is_terminal(self) -> None:
        assert is_terminal_contract(ContractKind.ROUTER_RESULT, _router("none"), LF00_TERMINAL)

    def test_router_result_that_delegates_is_not(self) -> None:
        """The failure this rule exists for: decided intake, never invoked it."""
        assert not is_terminal_contract(
            ContractKind.ROUTER_RESULT, _router("intake"), LF00_TERMINAL
        )

    def test_delegation_rule_applies_even_when_every_kind_is_allowed(self) -> None:
        assert not is_terminal_contract(ContractKind.ROUTER_RESULT, _router("intake"), ALL_KINDS)

    def test_missing_target_is_treated_as_answering(self) -> None:
        """Absent target cannot be a delegation; let contract validation judge it."""
        assert is_terminal_contract(ContractKind.ROUTER_RESULT, {"outcome": "failure"}, ALL_KINDS)

    def test_intake_result_is_never_subject_to_the_router_rule(self) -> None:
        """An IntakeResult may carry a 'target'-like key without being a hand-off."""
        payload = {"outcome": "requestComplete", "target": "intake"}
        assert is_terminal_contract(ContractKind.INTAKE_RESULT, payload, LF00_TERMINAL)


class TestTerminalRejectionReason:
    """Rejections must be explainable without echoing the payload."""

    def test_terminal_contract_has_no_reason(self) -> None:
        assert terminal_rejection_reason(ContractKind.INTAKE_RESULT, {}, LF00_TERMINAL) is None

    def test_undeclared_kind_names_the_kind(self) -> None:
        reason = terminal_rejection_reason(ContractKind.DATA_OPERATION_RESULT, {}, LF00_TERMINAL)
        assert reason is not None
        assert "data-operation-result" in reason

    def test_delegating_router_result_explains_the_unfinished_turn(self) -> None:
        reason = terminal_rejection_reason(
            ContractKind.ROUTER_RESULT, _router("intake"), LF00_TERMINAL
        )
        assert reason is not None
        assert "unfinished" in reason

    def test_reason_does_not_leak_payload_contents(self) -> None:
        payload = {"outcome": "routed", "target": "intake", "safe_message": "SENSITIVE-VALUE"}
        reason = terminal_rejection_reason(ContractKind.ROUTER_RESULT, payload, LF00_TERMINAL)
        assert reason is not None
        assert "SENSITIVE-VALUE" not in reason
