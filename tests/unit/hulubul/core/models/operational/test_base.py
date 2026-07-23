"""Tests for strict base models and constrained types."""
import pytest
from pydantic import ValidationError
from uuid import uuid4

from hulubul.core.models.operational.base import (
    StrictModel,
    VersionedContract,
    HumanSuppliedText,
    NonBlankText,
    SessionId,
    ActorUrn,
    RequestId,
)


class TestStrictModel:
    """StrictModel enforces strict validation."""

    def test_forbids_extra_fields(self):
        """Extra fields are forbidden."""

        class Model(StrictModel):
            value: str

        with pytest.raises(ValidationError):
            Model(value="test", extra="not_allowed")

    def test_strict_type_checking(self):
        """Strict mode rejects type coercion."""

        class Model(StrictModel):
            count: int

        # Strict=True means no string-to-int coercion
        with pytest.raises(ValidationError):
            Model(count="123")

    def test_strips_whitespace(self):
        """Whitespace is stripped from strings."""

        class Model(StrictModel):
            text: str

        m = Model(text="  hello  ")
        assert m.text == "hello"

    def test_frozen(self):
        """Models are immutable."""

        class Model(StrictModel):
            value: str

        m = Model(value="test")
        with pytest.raises(Exception):
            m.value = "changed"


class TestVersionedContract:
    """VersionedContract adds schema version and correlation ID."""

    def test_has_schema_version(self):
        """Schema version defaults to 1.0.0."""
        contract = VersionedContract(correlation_id=uuid4())
        assert contract.schema_version == "1.0.0"

    def test_requires_correlation_id(self):
        """Correlation ID is required."""
        with pytest.raises(ValidationError):
            VersionedContract()


class TestHumanSuppliedText:
    """HumanSuppliedText is 1-4000 chars after stripping."""

    @pytest.mark.parametrize(
        ("text", "valid"),
        [
            ("x", True),
            ("hello", True),
            ("x" * 4000, True),
            ("", False),
            ("x" * 4001, False),
            ("  ", False),
            ("  x  ", True),
        ],
    )
    def test_text_length_boundary(self, text, valid):
        """Text must be 1-4000 chars after stripping whitespace."""

        class Model(StrictModel):
            text: HumanSuppliedText

        if valid:
            m = Model(text=text)
            assert len(m.text) >= 1 and len(m.text) <= 4000
        else:
            with pytest.raises(ValidationError):
                Model(text=text)


class TestNonBlankText:
    """NonBlankText is 1+ chars, not whitespace-only."""

    def test_rejects_empty(self):
        """Empty string is invalid."""

        class Model(StrictModel):
            text: NonBlankText

        with pytest.raises(ValidationError):
            Model(text="")

    def test_rejects_whitespace_only(self):
        """Whitespace-only is invalid after stripping."""

        class Model(StrictModel):
            text: NonBlankText

        with pytest.raises(ValidationError):
            Model(text="   ")

    def test_accepts_nonempty(self):
        """Non-empty text is valid."""

        class Model(StrictModel):
            text: NonBlankText

        m = Model(text="hello")
        assert m.text == "hello"


class TestContractKind:
    """ContractKind enumeration has exact 11 values."""

    def test_contract_kind_inventory(self):
        """ContractKind has exactly 11 values."""
        from hulubul.core.models.operational.base import ContractKind

        expected = {
            "main-flow-input",
            "router-input",
            "intake-input",
            "routing-context",
            "router-result",
            "intake-facts",
            "intake-result",
            "data-operation-request",
            "data-operation-result",
            "delivery-request-snapshot",
            "operational-error",
        }
        actual = {ck.value for ck in ContractKind}
        assert actual == expected
