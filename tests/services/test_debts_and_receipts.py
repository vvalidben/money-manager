"""Debts and loans, and receipts attached to transactions."""

from datetime import date
from pathlib import Path

import pytest

from money_manager.core.errors import NotFoundError, ValidationError
from money_manager.domain.debts import DebtDirection
from money_manager.domain.entities import Account, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.services import AppServices

# Today is 15 Jun 2026 (tests.services.support).
PNG = b"\x89PNG\r\n\x1a\n" + bytes(64)
PDF = b"%PDF-1.7\n" + bytes(64)


@pytest.fixture
def bank(app_services: AppServices) -> Account:
    return app_services.accounts.create("Bank", opening_balance="10000",
                                        opening_date=date(2026, 1, 1))


class TestDebts:
    def test_lending_moves_money_without_counting_as_spending(
            self, app_services: AppServices, bank: Account) -> None:
        debt = app_services.debts.create("Sami", direction="lent", amount="2000",
                                         start_date=date(2026, 5, 1), account_id=bank.id,
                                         due_date=date(2026, 9, 1))
        assert debt.direction is DebtDirection.LENT and debt.remaining == Money.of("2000")
        [moved] = app_services.transactions.list()
        assert (moved.type, moved.amount, moved.description) == (
            TransactionType.ADJUSTMENT_OUT, Money.of("2000"), "Loan to Sami")
        assert app_services.balances.balance(bank.id) == Money.of("8000")
        # Net worth is unchanged: the money left the account but is owed back.
        assert app_services.investments.summary().net_worth == Money.of("10000")
        assert app_services.debts.summary().owed_to_you == Money.of("2000")

    def test_repayments(self, app_services: AppServices, bank: Account) -> None:
        debt = app_services.debts.create("Sami", direction="lent", amount="2000",
                                         start_date=date(2026, 5, 1), account_id=bank.id)
        debt = app_services.debts.record_payment(debt.id, "500", date(2026, 6, 1),
                                                 account_id=bank.id, note="first")
        assert (debt.repaid, debt.remaining) == (Money.of("500"), Money.of("1500"))
        assert app_services.balances.balance(bank.id) == Money.of("8500")
        with pytest.raises(ValidationError, match="Only 1,500.00 MAD is left"):
            app_services.debts.record_payment(debt.id, "1500.01", date(2026, 6, 2))
        with pytest.raises(ValidationError, match="before the debt started"):
            app_services.debts.record_payment(debt.id, "10", date(2026, 4, 1))
        debt = app_services.debts.record_payment(debt.id, "1500", date(2026, 6, 10))
        assert debt.is_settled and app_services.debts.list()[-1].id == debt.id
        # Deleting a repayment deletes the adjustment it recorded.
        debt = app_services.debts.delete_payment(debt.payments[0].id)
        assert debt.remaining == Money.of("500")
        assert app_services.balances.balance(bank.id) == Money.of("8000")

    def test_borrowing(self, app_services: AppServices, bank: Account) -> None:
        car = app_services.debts.create("Car loan", direction="borrowed", amount="60000",
                                        start_date=date(2026, 2, 1))
        assert app_services.transactions.list() == []  # no account: only tracked
        app_services.debts.record_payment(car.id, "2500", date(2026, 3, 1), account_id=bank.id)
        assert app_services.balances.balance(bank.id) == Money.of("7500")
        summary = app_services.debts.summary()
        assert (summary.you_owe, summary.net) == (Money.of("57500"), Money.of("-57500"))
        assert app_services.investments.summary().net_worth == Money.of("-50000")

    def test_net_worth_history_counts_loans(self, app_services: AppServices,
                                            bank: Account) -> None:
        debt = app_services.debts.create("Sami", direction="lent", amount="1000",
                                         start_date=date(2026, 3, 10), account_id=bank.id)
        app_services.debts.record_payment(debt.id, "400", date(2026, 5, 2), account_id=bank.id)
        points = {p.month.month: p for p in app_services.net_worth.history()}
        assert points[2].loans == Money.zero()
        assert (points[3].balance, points[3].loans) == (Money.of("9000"), Money.of("1000"))
        assert points[5].loans == Money.of("600")
        assert all(p.net_worth == Money.of("10000") for p in points.values())

    def test_edit_and_delete(self, app_services: AppServices, bank: Account) -> None:
        debt = app_services.debts.create("Sami", direction="lent", amount="100",
                                         start_date=date(2026, 6, 1), account_id=bank.id)
        debt = app_services.debts.update(debt.id, "Sami B.", due_date=date(2026, 12, 31),
                                         notes="for the car")
        assert (debt.name, debt.due_date, debt.notes) == ("Sami B.", date(2026, 12, 31),
                                                          "for the car")
        assert not debt.is_overdue(date(2026, 12, 31)) and debt.is_overdue(date(2027, 1, 1))
        app_services.debts.delete(debt.id)
        assert app_services.debts.list() == []
        assert len(app_services.transactions.list()) == 1  # the money movement stays
        with pytest.raises(NotFoundError):
            app_services.debts.get(debt.id)

    @pytest.mark.parametrize(("changes", "field"), [
        ({"name": " "}, "name"), ({"direction": "gift"}, "direction"),
        ({"amount": "0"}, "amount"), ({"start_date": date(2026, 7, 1)}, "start_date"),
        ({"due_date": date(2026, 1, 1)}, "due_date"),
    ])
    def test_validation(self, app_services: AppServices, changes: dict[str, object],
                        field: str) -> None:
        values: dict[str, object] = {"name": "Sami", "direction": "lent", "amount": "10",
                                     "start_date": date(2026, 6, 1)}
        values.update(changes)
        name = values.pop("name")
        with pytest.raises(ValidationError) as caught:
            app_services.debts.create(name, **values)  # type: ignore[arg-type]
        assert caught.value.field == field


class TestReceipts:
    @pytest.fixture
    def expense(self, app_services: AppServices, bank: Account) -> int:
        food = app_services.categories.create("Food", CategoryKind.EXPENSE)
        return app_services.transactions.create(TransactionDraft(
            bank.id, TransactionType.EXPENSE, "45", date(2026, 6, 3), food.id)).id

    def test_attach_open_and_remove(self, app_services: AppServices, expense: int,
                                    tmp_path: Path) -> None:
        (tmp_path / "ticket.png").write_bytes(PNG)
        (tmp_path / "invoice.pdf").write_bytes(PDF)
        first = app_services.receipts.add(expense, tmp_path / "ticket.png")
        app_services.receipts.add(expense, tmp_path / "invoice.pdf")
        assert [(r.file_name, r.media_type) for r in app_services.receipts.list(expense)] == [
            ("ticket.png", "image/png"), ("invoice.pdf", "application/pdf")]
        assert app_services.receipts.counts([expense, 999]) == {expense: 2}
        exported = app_services.receipts.export(first.id, tmp_path / "out")
        assert exported.read_bytes() == PNG
        app_services.receipts.delete(first.id)
        assert len(app_services.receipts.list(expense)) == 1

    def test_deleted_with_the_transaction(self, app_services: AppServices, expense: int,
                                          tmp_path: Path) -> None:
        (tmp_path / "t.png").write_bytes(PNG)
        app_services.receipts.add(expense, tmp_path / "t.png")
        app_services.transactions.delete(expense)
        assert app_services.receipts.counts([expense]) == {}

    @pytest.mark.parametrize(("name", "content", "message"), [
        ("notes.txt", b"hello", "photo"),
        ("fake.png", b"MZ\x90\x00 not a png", "do not match"),
        ("empty.pdf", b"", "empty"),
    ])
    def test_refused_files(self, app_services: AppServices, expense: int, tmp_path: Path,
                           name: str, content: bytes, message: str) -> None:
        (tmp_path / name).write_bytes(content)
        with pytest.raises(ValidationError, match=message):
            app_services.receipts.add(expense, tmp_path / name)

    def test_size_limit(self, app_services: AppServices, expense: int, tmp_path: Path,
                        monkeypatch: pytest.MonkeyPatch) -> None:
        from money_manager.services import receipt_service

        monkeypatch.setattr(receipt_service, "MAX_RECEIPT_BYTES", 10)
        (tmp_path / "big.png").write_bytes(PNG)
        with pytest.raises(ValidationError, match="larger than"):
            app_services.receipts.add(expense, tmp_path / "big.png")
