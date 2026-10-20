"""Receipts attached to transactions (photos or PDFs, kept in the database).

Files are checked before they are stored: an allowed extension, a size limit,
and contents that really start like that kind of file. They are saved in the
database so backups, safety copies, restores and resets always include them;
deleting the transaction deletes its receipts.
"""

# Deferred annotations: the ``list`` method would otherwise shadow the built-in.
from __future__ import annotations

import logging
from pathlib import Path

from money_manager.core.errors import NotFoundError, ValidationError
from money_manager.domain.receipts import (
    MAX_RECEIPT_BYTES,
    MAX_RECEIPTS_PER_TRANSACTION,
    RECEIPT_TYPES,
    Receipt,
    matches_signature,
)
from money_manager.domain.validation import validate_id
from money_manager.persistence.database import Database
from money_manager.persistence.models import ReceiptModel
from money_manager.persistence.repositories import ReceiptRepository, TransactionRepository
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

MAX_FILE_NAME_LENGTH = 200


def _to_domain(model: ReceiptModel) -> Receipt:
    return Receipt(model.id, model.transaction_id, model.file_name, model.media_type,
                   model.size, model.created_at)


class ReceiptService:
    def __init__(self, database: Database) -> None:
        self._database = database

    def list(self, transaction_id: int) -> list[Receipt]:
        with self._database.session() as session:
            return [_to_domain(m) for m in ReceiptRepository(session).for_transaction(
                validate_id(transaction_id, "transaction_id"))]

    def counts(self, transaction_ids: list[int]) -> dict[int, int]:
        """How many receipts each transaction has (only those with some)."""
        with self._database.session() as session:
            return ReceiptRepository(session).counts(transaction_ids)

    def add(self, transaction_id: int, path: Path) -> Receipt:
        transaction_id = validate_id(transaction_id, "transaction_id")
        media_type = RECEIPT_TYPES.get(Path(path).suffix.lower())
        if media_type is None:
            raise ValidationError(tr("Choose a photo (JPG, PNG, WebP, GIF, BMP) or a PDF."), "path")
        try:
            size = Path(path).stat().st_size
            if size > MAX_RECEIPT_BYTES:
                raise ValidationError(
                    tr("The file is larger than {0} MB.", MAX_RECEIPT_BYTES // (1024 * 1024)), "path")
            content = Path(path).read_bytes()
        except OSError as exc:
            raise ValidationError(tr("Could not read the file: {0}", exc.strerror or exc),
                                  "path") from exc
        if not content:
            raise ValidationError(tr("The file is empty."), "path")
        if not matches_signature(media_type, content):
            raise ValidationError(tr("The file's contents do not match its type."), "path")
        name = Path(path).name[-MAX_FILE_NAME_LENGTH:]
        with self._database.session() as session:
            if TransactionRepository(session).get(transaction_id) is None:
                raise NotFoundError(tr("Transaction {0!r} does not exist.", transaction_id))
            receipts = ReceiptRepository(session)
            if len(receipts.for_transaction(transaction_id)) >= MAX_RECEIPTS_PER_TRANSACTION:
                raise ValidationError(tr("A transaction can have at most {0} receipts.", MAX_RECEIPTS_PER_TRANSACTION), "path")
            model = receipts.add(ReceiptModel(transaction_id=transaction_id, file_name=name,
                                              media_type=media_type, size=len(content),
                                              content=content))
            receipt = _to_domain(model)
        logger.info("Attached receipt %s to transaction %s", receipt.id, transaction_id)
        return receipt

    def content(self, receipt_id: int) -> tuple[Receipt, bytes]:
        with self._database.session() as session:
            model = self._require(session, receipt_id)
            return _to_domain(model), bytes(model.content)

    def export(self, receipt_id: int, folder: Path) -> Path:
        """Write the receipt to ``folder`` (to open it) and return the file."""
        receipt, content = self.content(receipt_id)
        safe = "".join(c if c.isalnum() or c in " ._-()" else "_" for c in receipt.file_name)
        target = Path(folder) / f"{receipt.id}-{safe or 'receipt'}"
        try:
            Path(folder).mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        except OSError as exc:
            raise ValidationError(tr("Could not write the file: {0}", exc.strerror or exc),
                                  "path") from exc
        return target

    def delete(self, receipt_id: int) -> None:
        with self._database.session() as session:
            ReceiptRepository(session).delete(self._require(session, receipt_id))
        logger.info("Deleted receipt %s", receipt_id)

    @staticmethod
    def _require(session, receipt_id: int) -> ReceiptModel:  # noqa: ANN001
        model = ReceiptRepository(session).get(validate_id(receipt_id, "receipt_id"))
        if model is None:
            raise NotFoundError(tr("Receipt {0!r} does not exist.", receipt_id))
        return model
