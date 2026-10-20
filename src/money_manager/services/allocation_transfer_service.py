"""Moving money between allocations and Available.

A transfer only reorganises existing money: it creates no transaction, so the
real balance cannot change. The source must hold the full amount.
"""

import logging
from collections.abc import Callable
from datetime import date

from sqlalchemy.orm import Session

from money_manager.core.errors import ConflictError, NotFoundError, ValidationError
from money_manager.domain.entities import Allocation, AllocationTransfer
from money_manager.domain.money import DEFAULT_CURRENCY, AmountInput
from money_manager.domain.validation import is_record_id, validate_id, validate_transfer
from money_manager.persistence.database import Database
from money_manager.persistence.mappers import allocation_to_domain, transfer_to_domain
from money_manager.persistence.models import AllocationTransferModel
from money_manager.persistence.repositories import (
    AllocationRepository,
    AllocationTransferRepository,
)
from money_manager.services.allocation_ledger import AllocationLedger
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)


class AllocationTransferService:
    def __init__(
        self,
        database: Database,
        *,
        today: Callable[[], date] = date.today,
        base_currency: str = DEFAULT_CURRENCY,
    ) -> None:
        self._database = database
        self._today = today
        self._currency = base_currency

    def transfer(
        self,
        *,
        from_allocation_id: int | None,
        to_allocation_id: int | None,
        amount: AmountInput,
        on: date | None = None,
        note: str = "",
    ) -> AllocationTransfer:
        """Move ``amount`` from one allocation (None = Available) to another."""
        with self._database.session() as session:
            transfer = transfer_in_session(
                session,
                from_allocation_id=from_allocation_id,
                to_allocation_id=to_allocation_id,
                amount=amount,
                on=on,
                note=note,
                currency=self._currency,
                today=self._today(),
            )
        logger.info("Recorded allocation transfer %s", transfer.id)
        return transfer

    def get(self, transfer_id: int) -> AllocationTransfer:
        with self._database.session() as session:
            return transfer_to_domain(
                _require(AllocationTransferRepository(session), transfer_id), self._currency
            )

    def list(self, allocation_id: int | None = None) -> list[AllocationTransfer]:
        with self._database.session() as session:
            models = AllocationTransferRepository(session).list(allocation_id)
            return [transfer_to_domain(m, self._currency) for m in models]

    def undo(self, transfer_id: int) -> None:
        """Delete a transfer, returning its money to the source.

        Refused if the destination no longer holds the amount (it was spent or
        moved on) or if the source allocation has since been archived.
        """
        with self._database.session() as session:
            repository = AllocationTransferRepository(session)
            model = _require(repository, transfer_id)
            source = _load(session, model.from_allocation_id, "from_allocation_id")
            destination = _load(session, model.to_allocation_id, "to_allocation_id")
            if source is not None and source.is_archived:
                raise ConflictError(
                    tr("The allocation '{0}' is archived; restore it before undoing.", source.name)
                )
            amount = transfer_to_domain(model, self._currency).amount
            AllocationLedger(session, self._currency).require_funds(destination, amount)
            repository.delete(model)
        logger.info("Undid allocation transfer %s", transfer_id)


def transfer_in_session(
    session: Session,
    *,
    from_allocation_id: int | None,
    to_allocation_id: int | None,
    amount: AmountInput,
    on: date | None,
    note: str,
    currency: str,
    today: date,
) -> AllocationTransfer:
    """Validate and record a transfer inside the caller's unit of work."""
    source = _load(session, from_allocation_id, "from_allocation_id")
    destination = _load(session, to_allocation_id, "to_allocation_id")
    valid = validate_transfer(
        source=source,
        destination=destination,
        amount=amount,
        occurred_on=today if on is None else on,
        note=note,
        currency=currency,
        today=today,
    )
    AllocationLedger(session, currency).require_funds(source, valid.amount)
    model = AllocationTransferRepository(session).add(
        AllocationTransferModel(
            from_allocation_id=valid.from_allocation_id,
            to_allocation_id=valid.to_allocation_id,
            amount_minor=valid.amount.minor_units,
            occurred_on=valid.occurred_on,
            note=valid.note,
        )
    )
    return transfer_to_domain(model, currency)


def _load(session: Session, allocation_id: int | None, field: str) -> Allocation | None:
    """None stays None (Available); an unknown id is a validation error."""
    if allocation_id is None:
        return None
    model = AllocationRepository(session).get(validate_id(allocation_id, field))
    if model is None:
        raise ValidationError(tr("The selected allocation does not exist."), field)
    return allocation_to_domain(model)


def _require(repository: AllocationTransferRepository, transfer_id: int) -> AllocationTransferModel:
    model = repository.get(transfer_id) if is_record_id(transfer_id) else None
    if model is None:
        raise NotFoundError(tr("Transfer {0!r} does not exist.", transfer_id))
    return model
