"""Transfers between the user's own accounts (bank → cash wallet, paying a card…).

A transfer is real money movement between two accounts that leaves the total
unchanged. It is stored as two balance adjustments — out of one account, into
the other — tied together by an ``account_transfers`` row. Adjustments already
change balances without counting as income, spending or savings, so every
total and statistic stays right without a special case. Both sides are created
in one unit of work and removed together; neither can be edited or deleted on
its own.
"""

import logging
from collections.abc import Callable
from datetime import date

from sqlalchemy.orm import Session

from money_manager.core.errors import NotFoundError, ValidationError
from money_manager.domain.entities import AccountTransfer, TransactionDraft
from money_manager.domain.enums import TransactionType
from money_manager.domain.money import AmountInput, Money
from money_manager.domain.validation import validate_id
from money_manager.persistence.database import Database
from money_manager.persistence.models import AccountTransferModel, TransactionModel
from money_manager.persistence.repositories import (
    AccountRepository,
    AccountTransferRepository,
    TransactionRepository,
)
from money_manager.services.transaction_service import TransactionService

logger = logging.getLogger(__name__)


class AccountTransferService:
    def __init__(self, database: Database, transactions: TransactionService, *,
                 today: Callable[[], date] = date.today) -> None:
        self._database = database
        self._transactions = transactions
        self._today = today

    def create(self, from_account_id: int, to_account_id: int, amount: AmountInput,
               occurred_on: date, description: str = "") -> AccountTransfer:
        """Move ``amount`` from one account to another (validated like any entry)."""
        source_id = validate_id(from_account_id, "from_account_id")
        target_id = validate_id(to_account_id, "to_account_id")
        if source_id == target_id:
            raise ValidationError("Choose two different accounts.", "to_account_id")
        with self._database.session() as session:
            accounts = AccountRepository(session)
            source, target = accounts.get(source_id), accounts.get(target_id)
            if source is None:
                raise ValidationError("The account to transfer from does not exist.",
                                      "from_account_id")
            if target is None:
                raise ValidationError("The account to transfer to does not exist.",
                                      "to_account_id")
            note = description.strip() if isinstance(description, str) else ""
            out = self._transactions.create_in_session(session, TransactionDraft(
                source_id, TransactionType.ADJUSTMENT_OUT, amount, occurred_on,
                description=note or f"Transfer to {target.name}"))
            into = self._transactions.create_in_session(session, TransactionDraft(
                target_id, TransactionType.ADJUSTMENT_IN, amount, occurred_on,
                description=note or f"Transfer from {source.name}"))
            model = AccountTransferRepository(session).add(
                AccountTransferModel(out_transaction_id=out.id, in_transaction_id=into.id))
            transfer = _to_domain(session, model)
        logger.info("Recorded account transfer %s", transfer.id)
        return transfer

    def get(self, transfer_id: int) -> AccountTransfer:
        with self._database.session() as session:
            return _to_domain(session, _require(session, transfer_id))

    def list(self) -> list[AccountTransfer]:
        with self._database.session() as session:
            return [_to_domain(session, model)
                    for model in AccountTransferRepository(session).list()]

    def by_transaction(self) -> dict[int, AccountTransfer]:
        """Every transfer, keyed by the id of each of its two sides."""
        sides: dict[int, AccountTransfer] = {}
        for transfer in self.list():
            sides[transfer.out_transaction_id] = transfer
            sides[transfer.in_transaction_id] = transfer
        return sides

    def for_transaction(self, transaction_id: int) -> AccountTransfer | None:
        with self._database.session() as session:
            model = AccountTransferRepository(session).for_transaction(transaction_id)
            return None if model is None else _to_domain(session, model)

    def delete(self, transfer_id: int) -> None:
        """Remove the transfer and both of its sides."""
        with self._database.session() as session:
            model = _require(session, transfer_id)
            transactions = TransactionRepository(session)
            sides = [transactions.get(model.out_transaction_id),
                     transactions.get(model.in_transaction_id)]
            AccountTransferRepository(session).delete(model)
            for side in sides:
                if side is not None:
                    transactions.delete(side)
        logger.info("Deleted account transfer %s", transfer_id)


def _require(session: Session, transfer_id: int) -> AccountTransferModel:
    model = AccountTransferRepository(session).get(validate_id(transfer_id, "transfer_id"))
    if model is None:
        raise NotFoundError(f"Transfer {transfer_id!r} does not exist.")
    return model


def _to_domain(session: Session, model: AccountTransferModel) -> AccountTransfer:
    out = session.get(TransactionModel, model.out_transaction_id)
    into = session.get(TransactionModel, model.in_transaction_id)
    assert out is not None and into is not None  # RESTRICT keeps both sides
    return AccountTransfer(
        id=model.id,
        from_account_id=out.account_id,
        to_account_id=into.account_id,
        amount=Money.from_minor_units(out.amount_minor, out.currency),
        occurred_on=out.occurred_on,
        description=out.description,
        out_transaction_id=out.id,
        in_transaction_id=into.id,
    )
