from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from money_manager.persistence.models import RecurringEntryModel


class RecurringRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> Sequence[RecurringEntryModel]:
        return self._session.scalars(select(RecurringEntryModel).order_by(
            RecurringEntryModel.next_date, RecurringEntryModel.id)).all()

    def due(self, today: date) -> Sequence[RecurringEntryModel]:
        return self._session.scalars(select(RecurringEntryModel).where(
            RecurringEntryModel.is_active.is_(True), RecurringEntryModel.next_date <= today,
        ).order_by(RecurringEntryModel.next_date, RecurringEntryModel.id)).all()

    def get(self, entry_id: int) -> RecurringEntryModel | None:
        return self._session.get(RecurringEntryModel, entry_id)

    def add(self, entry: RecurringEntryModel) -> RecurringEntryModel:
        self._session.add(entry)
        self._session.flush()
        return entry

    def delete(self, entry: RecurringEntryModel) -> None:
        self._session.delete(entry)
        self._session.flush()
