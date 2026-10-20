"""Turn domain transactions into display rows (pure presentation, no Qt)."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from money_manager.domain.entities import AccountTransfer, Transaction
from money_manager.ui.formatting import format_date, format_signed_money, type_label
from money_manager.core.i18n import tr

NO_DESCRIPTION = tr("(no description)")
NO_CATEGORY = "—"
TRANSFER_TYPE = tr("Transfer")


PAPERCLIP = "\U0001F4CE"

@dataclass(frozen=True, slots=True)
class TransferSide:
    """How one side of a transfer between accounts is shown."""

    transfer_id: int
    label: str  # "To Cash wallet" / "From Bank"


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
    transfer_id: int | None = None  # set when the row is one side of an account transfer
    receipts: int = 0  # receipts attached (a paperclip follows the description)


def build_rows(
    transactions: Iterable[Transaction],
    category_names: Mapping[int, str],
    allocation_names: Mapping[int, str],
    transfers: Mapping[int, TransferSide] | None = None,
    receipts: Mapping[int, int] | None = None,
) -> list[TransactionRow]:
    """``transfers`` maps the ids of transfer sides to how they are shown; ``receipts``
    the ids of transactions with receipts to how many."""
    sides = transfers or {}
    counts = receipts or {}
    return [_row(t, category_names, allocation_names, sides.get(t.id), counts.get(t.id, 0))
            for t in transactions]


def _row(
    transaction: Transaction,
    category_names: Mapping[int, str],
    allocation_names: Mapping[int, str],
    transfer: TransferSide | None = None,
    receipts: int = 0,
) -> TransactionRow:
    is_inflow = transaction.type.sign > 0
    details = []
    if receipts:
        details.append(tr("1 receipt attached") if receipts == 1 else tr("{0} receipts attached", receipts))
    if transfer is not None:
        details.append(tr("Transfer between your accounts: {0}", transfer.label.lower()))
    if transaction.allocation_id is not None:
        direction = tr("Put into") if is_inflow else tr("Paid from")
        details.append(f"{direction}: {allocation_names.get(transaction.allocation_id, '?')}")
    if transaction.notes:
        details.append(transaction.notes)
    return TransactionRow(
        transaction=transaction,
        date=format_date(transaction.occurred_on),
        description=(transaction.description or NO_DESCRIPTION)
        + (f" {PAPERCLIP}" if receipts else ""),
        category=(
            transfer.label if transfer is not None
            else NO_CATEGORY if transaction.category_id is None
            else category_names.get(transaction.category_id, "?")
        ),
        type=TRANSFER_TYPE if transfer is not None else type_label(transaction.type),
        amount=format_signed_money(transaction.signed_amount),
        is_inflow=is_inflow,
        tooltip="\n".join(details),
        transfer_id=None if transfer is None else transfer.transfer_id,
        receipts=receipts,
    )


def transfer_sides(transfers: Mapping[int, AccountTransfer],
                   account_names: Mapping[int, str]) -> dict[int, TransferSide]:
    """Display labels for every transfer side (as from ``by_transaction()``)."""
    sides = {}
    for transaction_id, transfer in transfers.items():
        if transaction_id == transfer.out_transaction_id:
            label = tr("To {0}", account_names.get(transfer.to_account_id, '?'))
        else:
            label = tr("From {0}", account_names.get(transfer.from_account_id, '?'))
        sides[transaction_id] = TransferSide(transfer.id, label)
    return sides
