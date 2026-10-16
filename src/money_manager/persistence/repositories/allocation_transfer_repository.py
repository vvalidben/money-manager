from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from money_manager.persistence.models import AllocationTransferModel


class AllocationTransferRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, transfer_id: int) -> AllocationTransferModel | None:
        return self._session.get(AllocationTransferModel, transfer_id)

    def list(self, allocation_id: int | None = None) -> Sequence[AllocationTransferModel]:
        """Transfers newest first, optionally only those touching ``allocation_id``."""
        stmt = select(AllocationTransferModel).order_by(
            AllocationTransferModel.occurred_on.desc(), AllocationTransferModel.id.desc()
        )
        if allocation_id is not None:
            stmt = stmt.where(
                or_(
                    AllocationTransferModel.from_allocation_id == allocation_id,
                    AllocationTransferModel.to_allocation_id == allocation_id,
                )
            )
        return self._session.scalars(stmt).all()

    def add(self, transfer: AllocationTransferModel) -> AllocationTransferModel:
        self._session.add(transfer)
        self._session.flush()
        return transfer

    def delete(self, transfer: AllocationTransferModel) -> None:
        self._session.delete(transfer)
        self._session.flush()
