"""Turn domain transactions into display rows (pure presentation, no Qt)."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from money_manager.domain.entities import Transaction
from money_manager.ui.formatting import format_date, format_signed_money, type_label

NO_DESCRIPTION = "(no description)"
NO_CATEGORY = "—"


@dataclass(frozen=True, slots=True)
class TransactionRow:
    transaction: Transaction
    date: str
    description: str
    category: str
    type: str
    amount: str
    is_inflow: bool
    tooltip: str


def build_rows(
    transactions: Iterable[Transaction],
    category_names: Mapping[int, str],
    allocation_names: Mapping[int, str],
) -> list[TransactionRow]:
    return [_row(t, category_names, allocation_names) for t in transactions]


def _row(
    transaction: Transaction,
    category_names: Mapping[int, str],
    allocation_names: Mapping[int, str],
) -> TransactionRow:
    is_inflow = transaction.type.sign > 0
    details = []
    if transaction.allocation_id is not None:
        direction = "Put into" if is_inflow else "Paid from"
        details.append(f"{direction}: {allocation_names.get(transaction.allocation_id, '?')}")
    if transaction.notes:
        details.append(transaction.notes)
    return TransactionRow(
        transaction=transaction,
        date=format_date(transaction.occurred_on),
        description=transaction.description or NO_DESCRIPTION,
        category=(
            NO_CATEGORY
            if transaction.category_id is None
            else category_names.get(transaction.category_id, "?")
        ),
        type=type_label(transaction.type),
        amount=format_signed_money(transaction.signed_amount),
        is_inflow=is_inflow,
        tooltip="\n".join(details),
    )
