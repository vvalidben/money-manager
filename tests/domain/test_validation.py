from dataclasses import replace
from datetime import date, datetime

import pytest

from money_manager.core.errors import ValidationError
from money_manager.domain.entities import Account, Category, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.domain.validation import (
    MAX_DESCRIPTION_LENGTH,
    MAX_NOTES_LENGTH,
    clean_name,
    clean_text,
    normalize_name,
    validate_account,
    validate_date,
    validate_transaction,
)

TODAY = date(2026, 6, 15)
ACCOUNT = Account(
    id=1, name="Main", currency="MAD", opening_balance=Money.zero(), opening_date=date(2026, 1, 1)
)
FOOD = Category(id=10, name="Food", kind=CategoryKind.EXPENSE)
SALARY = Category(id=20, name="Salary", kind=CategoryKind.INCOME)
EXPENSE_DRAFT = TransactionDraft(
    account_id=1, type=TransactionType.EXPENSE, amount="300", occurred_on=date(2026, 6, 1),
    category_id=FOOD.id,
)


def _validate(draft: TransactionDraft, category: Category | None = FOOD, **kwargs: object):
    return validate_transaction(draft, account=ACCOUNT, category=category, today=TODAY, **kwargs)


class TestNames:
    def test_whitespace_is_collapsed(self) -> None:
        assert clean_name("  Eating   out ", field="name", max_length=40) == "Eating out"

    @pytest.mark.parametrize("raw", ["", "   ", None, 5])
    def test_rejects_empty_or_non_text(self, raw: object) -> None:
        with pytest.raises(ValidationError):
            clean_name(raw, field="name", max_length=40)

    def test_rejects_long_names(self) -> None:
        with pytest.raises(ValidationError, match="40"):
            clean_name("x" * 41, field="name", max_length=40)

    def test_normalisation_ignores_case_and_spacing(self) -> None:
        assert normalize_name(" FOOD  and Drinks") == normalize_name("food and drinks")

    def test_clean_text(self) -> None:
        assert clean_text(None, field="notes", max_length=5) == ""
        assert clean_text("  hi  ", field="notes", max_length=5) == "hi"
        with pytest.raises(ValidationError):
            clean_text("toolong", field="notes", max_length=5)


class TestDates:
    def test_accepts_today_and_past(self) -> None:
        assert validate_date(TODAY, field="d", today=TODAY) == TODAY
        assert validate_date(date(1900, 1, 1), field="d", today=TODAY) == date(1900, 1, 1)

    @pytest.mark.parametrize(
        "raw", [date(2026, 6, 16), date(1899, 12, 31), datetime(2026, 1, 1, 12), "2026-01-01", None]
    )
    def test_rejects_invalid_dates(self, raw: object) -> None:
        with pytest.raises(ValidationError):
            validate_date(raw, field="d", today=TODAY)


class TestAccount:
    def test_valid_account(self) -> None:
        valid = validate_account(
            name=" Bank ", opening_balance="-150.25", opening_date=TODAY, currency="MAD", today=TODAY
        )

        assert valid.name == "Bank"
        assert valid.opening_balance == Money.of("-150.25")

    @pytest.mark.parametrize(
        "overrides",
        [
            {"name": ""},
            {"opening_balance": 10.5},
            {"opening_balance": "1.001"},
            {"opening_date": date(2026, 6, 16)},
            {"currency": "mad"},
        ],
    )
    def test_invalid_account(self, overrides: dict[str, object]) -> None:
        fields: dict[str, object] = {
            "name": "Bank", "opening_balance": "0", "opening_date": TODAY, "currency": "MAD"
        }
        fields.update(overrides)
        with pytest.raises(ValidationError):
            validate_account(today=TODAY, **fields)  # type: ignore[arg-type]


class TestTransaction:
    def test_valid_expense(self) -> None:
        valid = _validate(replace(EXPENSE_DRAFT, description="  Lunch ", notes=" with team "))

        assert valid.type is TransactionType.EXPENSE
        assert valid.amount == Money.of("300.00", "MAD")
        assert valid.category_id == FOOD.id
        assert (valid.description, valid.notes) == ("Lunch", "with team")

    def test_type_can_be_a_string(self) -> None:
        assert _validate(replace(EXPENSE_DRAFT, type="expense")).type is TransactionType.EXPENSE

    def test_adjustment_without_category(self) -> None:
        draft = replace(EXPENSE_DRAFT, type=TransactionType.ADJUSTMENT_OUT, category_id=None)

        assert _validate(draft, category=None).category_id is None

    @pytest.mark.parametrize("amount", ["0", "0.00", "-300", 0, 12.5, "1.234", "", "abc"])
    def test_rejects_bad_amounts(self, amount: object) -> None:
        with pytest.raises(ValidationError) as info:
            _validate(replace(EXPENSE_DRAFT, amount=amount))  # type: ignore[arg-type]

        assert info.value.field == "amount"

    def test_rejects_invalid_type(self) -> None:
        with pytest.raises(ValidationError) as info:
            _validate(replace(EXPENSE_DRAFT, type="transfer"))

        assert info.value.field == "type"

    def test_rejects_date_before_opening(self) -> None:
        with pytest.raises(ValidationError, match="opening date"):
            _validate(replace(EXPENSE_DRAFT, occurred_on=date(2025, 12, 31)))

    def test_accepts_opening_day(self) -> None:
        assert _validate(replace(EXPENSE_DRAFT, occurred_on=ACCOUNT.opening_date)).occurred_on == (
            ACCOUNT.opening_date
        )

    def test_rejects_future_date(self) -> None:
        with pytest.raises(ValidationError, match="future"):
            _validate(replace(EXPENSE_DRAFT, occurred_on=date(2026, 6, 16)))

    def test_requires_category_for_expense(self) -> None:
        with pytest.raises(ValidationError, match="Choose a category"):
            _validate(replace(EXPENSE_DRAFT, category_id=None), category=None)

    def test_rejects_wrong_category_kind(self) -> None:
        with pytest.raises(ValidationError, match="income category"):
            _validate(replace(EXPENSE_DRAFT, category_id=SALARY.id), category=SALARY)

    def test_rejects_category_on_adjustment(self) -> None:
        draft = replace(EXPENSE_DRAFT, type=TransactionType.ADJUSTMENT_IN)

        with pytest.raises(ValidationError, match="do not use a category"):
            _validate(draft)

    def test_archived_category(self) -> None:
        archived = replace(FOOD, is_archived=True)

        with pytest.raises(ValidationError, match="archived"):
            _validate(EXPENSE_DRAFT, category=archived)
        assert _validate(EXPENSE_DRAFT, category=archived, keep_archived_category_id=FOOD.id)

    def test_text_limits(self) -> None:
        with pytest.raises(ValidationError):
            _validate(replace(EXPENSE_DRAFT, description="x" * (MAX_DESCRIPTION_LENGTH + 1)))
        with pytest.raises(ValidationError):
            _validate(replace(EXPENSE_DRAFT, notes="x" * (MAX_NOTES_LENGTH + 1)))

    def test_amount_takes_account_currency(self) -> None:
        eur_account = replace(ACCOUNT, currency="EUR")

        valid = validate_transaction(EXPENSE_DRAFT, account=eur_account, category=FOOD, today=TODAY)

        assert valid.amount.currency == "EUR"
