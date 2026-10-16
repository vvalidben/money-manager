from collections.abc import Collection, Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from money_manager.persistence.models import (
    InvestmentEntryModel,
    InvestmentModel,
    InvestmentValuationModel,
    TransactionModel,
)

# (entry, amount in minor units, date) — amount/date resolved from the backing
# transaction when the entry has one.
EntryRow = tuple[InvestmentEntryModel, int, date]


class InvestmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, investment_id: int) -> InvestmentModel | None:
        return self._session.get(InvestmentModel, investment_id)

    def list_all(self, include_archived: bool = True) -> Sequence[InvestmentModel]:
        stmt = select(InvestmentModel).order_by(InvestmentModel.normalized_name)
        if not include_archived:
            stmt = stmt.where(InvestmentModel.is_archived.is_(False))
        return self._session.scalars(stmt).all()

    def get_by_normalized_name(self, normalized_name: str) -> InvestmentModel | None:
        stmt = select(InvestmentModel).where(InvestmentModel.normalized_name == normalized_name)
        return self._session.scalars(stmt).one_or_none()

    def add(self, investment: InvestmentModel) -> InvestmentModel:
        self._session.add(investment)
        self._session.flush()
        return investment

    def delete(self, investment: InvestmentModel) -> None:
        self._session.delete(investment)
        self._session.flush()

    # ----------------------------------------------------------------- entries

    def entries(self, investment_ids: Collection[int]) -> list[EntryRow]:
        """Entries of the given investments with their effective amount and date, oldest first."""
        if not investment_ids:
            return []
        stmt = (
            select(InvestmentEntryModel, TransactionModel.amount_minor, TransactionModel.occurred_on)
            .outerjoin(TransactionModel, TransactionModel.id == InvestmentEntryModel.transaction_id)
            .where(InvestmentEntryModel.investment_id.in_(list(investment_ids)))
        )
        rows = [
            (entry, int(entry.amount_minor if entry.amount_minor is not None else tx_amount),
             entry.occurred_on if entry.occurred_on is not None else tx_date)
            for entry, tx_amount, tx_date in self._session.execute(stmt)
        ]
        rows.sort(key=lambda row: (row[2], row[0].id))
        return rows

    def get_entry(self, entry_id: int) -> InvestmentEntryModel | None:
        return self._session.get(InvestmentEntryModel, entry_id)

    def entry_for_transaction(self, transaction_id: int) -> InvestmentEntryModel | None:
        stmt = select(InvestmentEntryModel).where(
            InvestmentEntryModel.transaction_id == transaction_id
        )
        return self._session.scalars(stmt).one_or_none()

    def add_entry(self, entry: InvestmentEntryModel) -> InvestmentEntryModel:
        self._session.add(entry)
        self._session.flush()
        return entry

    def delete_entry(self, entry: InvestmentEntryModel) -> None:
        self._session.delete(entry)
        self._session.flush()

    # -------------------------------------------------------------- valuations

    def valuations(self, investment_ids: Collection[int]) -> Sequence[InvestmentValuationModel]:
        if not investment_ids:
            return []
        stmt = (
            select(InvestmentValuationModel)
            .where(InvestmentValuationModel.investment_id.in_(list(investment_ids)))
            .order_by(InvestmentValuationModel.valued_on, InvestmentValuationModel.id)
        )
        return self._session.scalars(stmt).all()

    def get_valuation(self, valuation_id: int) -> InvestmentValuationModel | None:
        return self._session.get(InvestmentValuationModel, valuation_id)

    def valuation_on(self, investment_id: int, day: date) -> InvestmentValuationModel | None:
        stmt = select(InvestmentValuationModel).where(
            InvestmentValuationModel.investment_id == investment_id,
            InvestmentValuationModel.valued_on == day,
        )
        return self._session.scalars(stmt).one_or_none()

    def add_valuation(self, valuation: InvestmentValuationModel) -> InvestmentValuationModel:
        self._session.add(valuation)
        self._session.flush()
        return valuation

    def delete_valuation(self, valuation: InvestmentValuationModel) -> None:
        self._session.delete(valuation)
        self._session.flush()
