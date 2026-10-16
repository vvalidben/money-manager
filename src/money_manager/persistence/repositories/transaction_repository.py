# Deferred annotations: the ``list`` method below would otherwise shadow the
# built-in ``list`` in later annotations inside the class body.
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import ColumnElement, Select, exists, func, or_, select
from sqlalchemy.orm import Session

from money_manager.core.errors import ValidationError
from money_manager.domain.entities import TransactionFilter
from money_manager.domain.enums import TransactionSort, TransactionType
from money_manager.domain.money import Money, parse_amount_text
from money_manager.persistence.models import CategoryModel, TransactionModel
from money_manager.persistence.models.transaction import signed_amount_minor

_LIKE_ESCAPE = "\\"


def _sort_column(sort: TransactionSort) -> ColumnElement[Any]:
    match sort:
        case TransactionSort.DATE:
            return TransactionModel.occurred_on
        case TransactionSort.DESCRIPTION:
            return func.lower(TransactionModel.description)
        case TransactionSort.CATEGORY:
            return func.lower(CategoryModel.name)
        case TransactionSort.TYPE:
            return TransactionModel.type
        case TransactionSort.AMOUNT:
            return signed_amount_minor()


def _escape_like(text: str) -> str:
    return (
        text.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2)
        .replace("%", _LIKE_ESCAPE + "%")
        .replace("_", _LIKE_ESCAPE + "_")
    )


def _search_condition(search: str) -> ColumnElement[bool]:
    pattern = f"%{_escape_like(search)}%"
    conditions: list[ColumnElement[bool]] = [
        TransactionModel.description.ilike(pattern, escape=_LIKE_ESCAPE),
        TransactionModel.notes.ilike(pattern, escape=_LIKE_ESCAPE),
        CategoryModel.name.ilike(pattern, escape=_LIKE_ESCAPE),
    ]
    try:
        amount = parse_amount_text(search)
    except ValidationError:
        pass
    else:
        conditions.append(TransactionModel.amount_minor == abs(Money(amount).minor_units))
    return or_(*conditions)


def _filtered(stmt: Select[Any], filters: TransactionFilter) -> Select[Any]:
    """Apply ``filters``; the category join is needed for search and sorting."""
    stmt = stmt.outerjoin(CategoryModel, CategoryModel.id == TransactionModel.category_id)
    if filters.account_id is not None:
        stmt = stmt.where(TransactionModel.account_id == filters.account_id)
    if filters.category_id is not None:
        stmt = stmt.where(TransactionModel.category_id == filters.category_id)
    if filters.types is not None:
        stmt = stmt.where(TransactionModel.type.in_([t.value for t in filters.types]))
    if filters.start is not None:
        stmt = stmt.where(TransactionModel.occurred_on >= filters.start)
    if filters.end is not None:
        stmt = stmt.where(TransactionModel.occurred_on <= filters.end)
    if filters.allocation_id is not None:
        stmt = stmt.where(TransactionModel.allocation_id == filters.allocation_id)
    if filters.search:
        stmt = stmt.where(_search_condition(filters.search))
    return stmt


class TransactionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, transaction_id: int) -> TransactionModel | None:
        return self._session.get(TransactionModel, transaction_id)

    def list(self, filters: TransactionFilter) -> Sequence[TransactionModel]:
        """All matching transactions, newest first."""
        return self.search(filters, TransactionSort.DATE, descending=True)

    def search(
        self,
        filters: TransactionFilter,
        sort: TransactionSort,
        *,
        descending: bool,
        offset: int = 0,
        limit: int | None = None,
    ) -> Sequence[TransactionModel]:
        column = _sort_column(sort)
        # Ties are broken by id so paging is stable.
        order = (
            (column.desc(), TransactionModel.id.desc())
            if descending
            else (column.asc(), TransactionModel.id.asc())
        )
        stmt = _filtered(select(TransactionModel), filters).order_by(*order).offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        return self._session.scalars(stmt).all()

    def count(self, filters: TransactionFilter) -> int:
        stmt = _filtered(select(func.count(TransactionModel.id)).select_from(TransactionModel), filters)
        return int(self._session.scalar(stmt) or 0)

    def totals_matching(self, filters: TransactionFilter) -> dict[TransactionType, int]:
        """Sum of amounts (minor units) per type over every matching transaction."""
        stmt = _filtered(
            select(TransactionModel.type, func.sum(TransactionModel.amount_minor)).select_from(
                TransactionModel
            ),
            filters,
        ).group_by(TransactionModel.type)
        return {
            TransactionType(type_value): int(total)
            for type_value, total in self._session.execute(stmt)
        }

    def daily_net_minor(self, until: date) -> list[tuple[date, int]]:
        """Net signed change per day (minor units), oldest first, up to ``until``."""
        stmt = (
            select(TransactionModel.occurred_on, func.sum(signed_amount_minor()))
            .where(TransactionModel.occurred_on <= until)
            .group_by(TransactionModel.occurred_on)
            .order_by(TransactionModel.occurred_on)
        )
        return [(day, int(total)) for day, total in self._session.execute(stmt)]

    def ledger_entries(
        self, start: date, end: date
    ) -> list[tuple[date, TransactionType, int | None, int]]:
        """(day, type, category id, amount sum in minor units) for [start, end].

        The single aggregate every analytic in ``domain.analytics`` is built from.
        """
        stmt = (
            select(
                TransactionModel.occurred_on,
                TransactionModel.type,
                TransactionModel.category_id,
                func.sum(TransactionModel.amount_minor),
            )
            .where(TransactionModel.occurred_on >= start, TransactionModel.occurred_on <= end)
            .group_by(TransactionModel.occurred_on, TransactionModel.type, TransactionModel.category_id)
            .order_by(TransactionModel.occurred_on)
        )
        return [
            (day, TransactionType(type_value), category_id, int(total))
            for day, type_value, category_id, total in self._session.execute(stmt)
        ]

    def expense_records(
        self, start: date, end: date
    ) -> list[tuple[date, str, int | None, int]]:
        """Individual expenses (day, description, category id, amount) in [start, end]."""
        stmt = (
            select(
                TransactionModel.occurred_on,
                TransactionModel.description,
                TransactionModel.category_id,
                TransactionModel.amount_minor,
            )
            .where(
                TransactionModel.type == TransactionType.EXPENSE.value,
                TransactionModel.occurred_on >= start,
                TransactionModel.occurred_on <= end,
            )
            .order_by(TransactionModel.occurred_on, TransactionModel.id)
        )
        return [tuple(row) for row in self._session.execute(stmt)]  # type: ignore[misc]

    def signed_total_minor(self) -> int:
        """Net effect of every transaction in every account, in minor units."""
        total = self._session.scalar(select(func.sum(signed_amount_minor())))
        return int(total or 0)

    def add(self, transaction: TransactionModel) -> TransactionModel:
        self._session.add(transaction)
        self._session.flush()
        return transaction

    def delete(self, transaction: TransactionModel) -> None:
        self._session.delete(transaction)
        self._session.flush()

    def exists_for_account(self, account_id: int) -> bool:
        stmt = select(exists().where(TransactionModel.account_id == account_id))
        return bool(self._session.scalar(stmt))

    def exists_for_category(self, category_id: int) -> bool:
        stmt = select(exists().where(TransactionModel.category_id == category_id))
        return bool(self._session.scalar(stmt))

    def earliest_date(self, account_id: int) -> date | None:
        stmt = select(func.min(TransactionModel.occurred_on)).where(
            TransactionModel.account_id == account_id
        )
        return self._session.scalar(stmt)

    def totals_by_type(
        self, account_id: int, as_of: date | None = None
    ) -> dict[TransactionType, int]:
        """Sum of amounts (integer minor units) per type, optionally up to ``as_of``.

        Summing integers in SQL is exact; no floating point is involved.
        """
        stmt = (
            select(TransactionModel.type, func.sum(TransactionModel.amount_minor))
            .where(TransactionModel.account_id == account_id)
            .group_by(TransactionModel.type)
        )
        if as_of is not None:
            stmt = stmt.where(TransactionModel.occurred_on <= as_of)
        return {
            TransactionType(type_value): int(total)
            for type_value, total in self._session.execute(stmt)
        }
