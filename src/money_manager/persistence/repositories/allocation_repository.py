from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from money_manager.persistence.models import (
    AllocationModel,
    AllocationTransferModel,
    TransactionModel,
)
from money_manager.persistence.models.transaction import signed_amount_minor


class AllocationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, allocation_id: int) -> AllocationModel | None:
        return self._session.get(AllocationModel, allocation_id)

    def list(self, include_archived: bool = False) -> Sequence[AllocationModel]:
        stmt = select(AllocationModel).order_by(AllocationModel.normalized_name, AllocationModel.id)
        if not include_archived:
            stmt = stmt.where(AllocationModel.is_archived.is_(False))
        return self._session.scalars(stmt).all()

    def get_by_normalized_name(self, normalized_name: str) -> AllocationModel | None:
        stmt = select(AllocationModel).where(AllocationModel.normalized_name == normalized_name)
        return self._session.scalars(stmt).one_or_none()

    def add(self, allocation: AllocationModel) -> AllocationModel:
        self._session.add(allocation)
        self._session.flush()
        return allocation

    def delete(self, allocation: AllocationModel) -> None:
        self._session.delete(allocation)
        self._session.flush()

    def has_history(self, allocation_id: int) -> bool:
        """True if any transfer or transaction references the allocation."""
        transfer_used = exists().where(
            or_(
                AllocationTransferModel.from_allocation_id == allocation_id,
                AllocationTransferModel.to_allocation_id == allocation_id,
            )
        )
        transaction_used = exists().where(TransactionModel.allocation_id == allocation_id)
        return bool(self._session.scalar(select(or_(transfer_used, transaction_used))))

    def balances_minor(self) -> dict[int, int]:
        """Balance of every allocation with activity, in integer minor units.

        balance = transfers in − transfers out + tagged income − tagged expenses
        """
        balances: defaultdict[int, int] = defaultdict(int)
        transfers_in = (
            select(AllocationTransferModel.to_allocation_id, func.sum(AllocationTransferModel.amount_minor))
            .where(AllocationTransferModel.to_allocation_id.is_not(None))
            .group_by(AllocationTransferModel.to_allocation_id)
        )
        transfers_out = (
            select(AllocationTransferModel.from_allocation_id, func.sum(AllocationTransferModel.amount_minor))
            .where(AllocationTransferModel.from_allocation_id.is_not(None))
            .group_by(AllocationTransferModel.from_allocation_id)
        )
        tagged_transactions = (
            select(TransactionModel.allocation_id, func.sum(signed_amount_minor()))
            .where(TransactionModel.allocation_id.is_not(None))
            .group_by(TransactionModel.allocation_id)
        )
        for allocation_id, total in self._session.execute(transfers_in):
            balances[allocation_id] += int(total)
        for allocation_id, total in self._session.execute(transfers_out):
            balances[allocation_id] -= int(total)
        for allocation_id, total in self._session.execute(tagged_transactions):
            balances[allocation_id] += int(total)
        return dict(balances)
