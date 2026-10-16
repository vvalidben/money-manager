from datetime import date

import pytest

from money_manager.core.errors import ValidationError
from money_manager.domain.allocation import AllocationBalance, AllocationSummary
from money_manager.domain.entities import Account, Allocation, Category, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.domain.validation import (
    validate_allocation_name,
    validate_transaction,
    validate_transfer,
)

TODAY = date(2026, 6, 15)
SAVINGS = Allocation(id=1, name="Savings")
INVESTMENTS = Allocation(id=2, name="Investments")
ARCHIVED = Allocation(id=3, name="Old", is_archived=True)


def _summary(total: str, **balances: str) -> AllocationSummary:
    rows = tuple(
        AllocationBalance(Allocation(id=i, name=name), Money.of(amount))
        for i, (name, amount) in enumerate(balances.items(), start=1)
    )
    return AllocationSummary(Money.of(total), rows)


class TestSummary:
    def test_available_is_what_is_left(self) -> None:
        summary = _summary("10000", Savings="3000", Investments="2000")

        assert summary.allocated_total == Money.of("5000")
        assert summary.available == Money.of("5000")
        assert summary.available + summary.allocated_total == summary.total_balance
        assert not summary.is_over_allocated
        assert summary.shortfall == Money.zero()

    def test_no_allocations_means_everything_is_available(self) -> None:
        assert _summary("1234.56").available == Money.of("1234.56")

    def test_over_allocation(self) -> None:
        summary = _summary("4000", Savings="3000", Investments="2000")

        assert summary.available == Money.of("-1000")
        assert summary.is_over_allocated
        assert summary.shortfall == Money.of("1000")

    def test_balance_of(self) -> None:
        summary = _summary("10000", Savings="3000")

        assert summary.balance_of(1) == Money.of("3000")
        assert summary.balance_of(99) == Money.zero()


class TestAllocationNames:
    @pytest.mark.parametrize("name", ["Savings", "Emergency Fund", "Gaming", "  Travel  "])
    def test_any_name(self, name: str) -> None:
        assert validate_allocation_name(name) == name.strip()

    @pytest.mark.parametrize("name", ["Available", " AVAILABLE ", "unallocated", "", "x" * 41])
    def test_rejected_names(self, name: str) -> None:
        with pytest.raises(ValidationError):
            validate_allocation_name(name)


class TestTransferValidation:
    def _validate(self, source: Allocation | None, destination: Allocation | None, **kw: object):
        fields: dict[str, object] = {"amount": "500", "occurred_on": TODAY, "note": ""}
        fields.update(kw)
        return validate_transfer(
            source=source, destination=destination, currency="MAD", today=TODAY, **fields
        )

    def test_available_to_allocation(self) -> None:
        valid = self._validate(None, INVESTMENTS, note=" top up ")

        assert (valid.from_allocation_id, valid.to_allocation_id) == (None, INVESTMENTS.id)
        assert valid.amount == Money.of("500")
        assert valid.note == "top up"

    def test_between_allocations_and_back_to_available(self) -> None:
        assert self._validate(SAVINGS, INVESTMENTS).from_allocation_id == SAVINGS.id
        assert self._validate(SAVINGS, None).to_allocation_id is None

    def test_available_to_available(self) -> None:
        with pytest.raises(ValidationError, match="does nothing"):
            self._validate(None, None)

    def test_same_allocation(self) -> None:
        with pytest.raises(ValidationError, match="different"):
            self._validate(SAVINGS, SAVINGS)

    @pytest.mark.parametrize(("source", "destination"), [(ARCHIVED, None), (None, ARCHIVED)])
    def test_archived_endpoints(
        self, source: Allocation | None, destination: Allocation | None
    ) -> None:
        with pytest.raises(ValidationError, match="archived"):
            self._validate(source, destination)

    @pytest.mark.parametrize("amount", ["0", "-5", 5.0, "0.001", "x"])
    def test_invalid_amounts(self, amount: object) -> None:
        with pytest.raises(ValidationError) as info:
            self._validate(None, SAVINGS, amount=amount)
        assert info.value.field == "amount"

    def test_future_date(self) -> None:
        with pytest.raises(ValidationError, match="future"):
            self._validate(None, SAVINGS, occurred_on=date(2026, 6, 16))


class TestTransactionAllocationRules:
    ACCOUNT = Account(1, "Main", "MAD", Money.zero(), date(2026, 1, 1))
    BILLS = Category(10, "Bills", CategoryKind.EXPENSE)

    def _draft(self, **kw: object) -> TransactionDraft:
        fields: dict[str, object] = {
            "account_id": 1, "type": TransactionType.EXPENSE, "amount": "100",
            "occurred_on": TODAY, "category_id": self.BILLS.id, "allocation_id": SAVINGS.id,
        }
        fields.update(kw)
        return TransactionDraft(**fields)  # type: ignore[arg-type]

    def _validate(self, draft: TransactionDraft, allocation: Allocation | None, **kw: object):
        category = self.BILLS if draft.category_id else None
        return validate_transaction(
            draft, account=self.ACCOUNT, category=category, today=TODAY,
            allocation=allocation, **kw,  # type: ignore[arg-type]
        )

    def test_tagged_expense(self) -> None:
        assert self._validate(self._draft(), SAVINGS).allocation_id == SAVINGS.id

    def test_untagged_expense(self) -> None:
        assert self._validate(self._draft(allocation_id=None), None).allocation_id is None

    def test_adjustments_cannot_be_tagged(self) -> None:
        draft = self._draft(type=TransactionType.ADJUSTMENT_OUT, category_id=None)

        with pytest.raises(ValidationError, match="Available"):
            self._validate(draft, SAVINGS)

    def test_unknown_allocation(self) -> None:
        with pytest.raises(ValidationError, match="does not exist"):
            self._validate(self._draft(allocation_id=99), None)

    def test_archived_allocation(self) -> None:
        draft = self._draft(allocation_id=ARCHIVED.id)

        with pytest.raises(ValidationError, match="archived"):
            self._validate(draft, ARCHIVED)
        assert self._validate(draft, ARCHIVED, keep_archived_allocation_id=ARCHIVED.id)
