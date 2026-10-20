"""Transaction types and category kinds."""

from enum import StrEnum

from money_manager.core.errors import ValidationError
from money_manager.core.i18n import tr


class CategoryKind(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"


class TransactionType(StrEnum):
    """Kinds of real money movement.

    Amounts are always stored as positive magnitudes; the type alone decides
    whether money enters (+) or leaves (−) the account. Adjustments correct
    the recorded balance to match reality and carry no category.
    """

    INCOME = "income"
    EXPENSE = "expense"
    ADJUSTMENT_IN = "adjustment_in"
    ADJUSTMENT_OUT = "adjustment_out"

    @property
    def sign(self) -> int:
        return 1 if self in _INFLOW_TYPES else -1

    @property
    def category_kind(self) -> CategoryKind | None:
        """The category kind this type requires, or None if it takes no category."""
        return _CATEGORY_KIND_BY_TYPE.get(self)

    @property
    def is_adjustment(self) -> bool:
        return self.category_kind is None

    @property
    def label(self) -> str:
        return tr(_LABELS[self])


class TransactionSort(StrEnum):
    DATE = "date"
    DESCRIPTION = "description"
    CATEGORY = "category"
    TYPE = "type"
    AMOUNT = "amount"  # signed: expenses sort below income


_INFLOW_TYPES = frozenset({TransactionType.INCOME, TransactionType.ADJUSTMENT_IN})
_CATEGORY_KIND_BY_TYPE = {
    TransactionType.INCOME: CategoryKind.INCOME,
    TransactionType.EXPENSE: CategoryKind.EXPENSE,
}
_LABELS = {
    TransactionType.INCOME: "income",
    TransactionType.EXPENSE: "expense",
    TransactionType.ADJUSTMENT_IN: "positive balance adjustment",
    TransactionType.ADJUSTMENT_OUT: "negative balance adjustment",
}


def parse_transaction_type(value: object) -> TransactionType:
    if isinstance(value, TransactionType):
        return value
    if isinstance(value, str):
        try:
            return TransactionType(value.strip().lower())
        except ValueError:
            pass
    allowed = ", ".join(t.value for t in TransactionType)
    raise ValidationError(tr("Invalid transaction type {0!r}; expected one of: {1}.", value, allowed), "type")


def parse_category_kind(value: object) -> CategoryKind:
    if isinstance(value, CategoryKind):
        return value
    if isinstance(value, str):
        try:
            return CategoryKind(value.strip().lower())
        except ValueError:
            pass
    allowed = ", ".join(k.value for k in CategoryKind)
    raise ValidationError(tr("Invalid category kind {0!r}; expected one of: {1}.", value, allowed), "kind")
