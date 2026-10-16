import pytest

from money_manager.core.errors import ValidationError
from money_manager.domain.enums import (
    CategoryKind,
    TransactionType,
    parse_category_kind,
    parse_transaction_type,
)


@pytest.mark.parametrize(
    ("transaction_type", "sign", "kind"),
    [
        (TransactionType.INCOME, 1, CategoryKind.INCOME),
        (TransactionType.EXPENSE, -1, CategoryKind.EXPENSE),
        (TransactionType.ADJUSTMENT_IN, 1, None),
        (TransactionType.ADJUSTMENT_OUT, -1, None),
    ],
)
def test_type_rules(transaction_type: TransactionType, sign: int, kind: CategoryKind | None) -> None:
    assert transaction_type.sign == sign
    assert transaction_type.category_kind is kind
    assert transaction_type.is_adjustment is (kind is None)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("income", TransactionType.INCOME),
        (" EXPENSE ", TransactionType.EXPENSE),
        ("adjustment_in", TransactionType.ADJUSTMENT_IN),
        (TransactionType.ADJUSTMENT_OUT, TransactionType.ADJUSTMENT_OUT),
    ],
)
def test_parse_transaction_type(raw: object, expected: TransactionType) -> None:
    assert parse_transaction_type(raw) is expected


@pytest.mark.parametrize("raw", ["transfer", "", "incomes", "savings", None, 1])
def test_invalid_transaction_type(raw: object) -> None:
    with pytest.raises(ValidationError) as info:
        parse_transaction_type(raw)

    assert info.value.field == "type"


def test_parse_category_kind() -> None:
    assert parse_category_kind("Income") is CategoryKind.INCOME
    with pytest.raises(ValidationError):
        parse_category_kind("savings")
