"""Subscriptions on a real database: CRUD, payments and duplicate prevention."""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from money_manager.core.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from money_manager.domain.entities import Account, Category, TransactionFilter
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.domain.subscriptions import Frequency, PaymentStatus
from money_manager.persistence.database import Database
from money_manager.services import (
    AccountService,
    BalanceService,
    CategoryService,
    SubscriptionService,
    TransactionService,
)
from tests.services.support import OPENING_DATE, TODAY, fixed_today


@pytest.fixture
def subscriptions(database: Database, transactions: TransactionService) -> SubscriptionService:
    return SubscriptionService(database, transactions, today=fixed_today)


@pytest.fixture
def bank(accounts: AccountService) -> Account:
    return accounts.create("Bank", opening_balance="5000", opening_date=OPENING_DATE)


@pytest.fixture
def streaming(categories: CategoryService) -> Category:
    return categories.create("Subscriptions", CategoryKind.EXPENSE)


def _netflix(subscriptions: SubscriptionService, streaming: Category, bank: Account | None = None,
             **overrides: object):
    fields: dict[str, object] = {
        "amount": "150", "frequency": Frequency.MONTHLY, "next_payment_date": date(2026, 6, 20),
        "category_id": streaming.id, "account_id": None if bank is None else bank.id,
    }
    fields.update(overrides)
    return subscriptions.create("Netflix", **fields)  # type: ignore[arg-type]


class TestCrud:
    def test_create_and_get(self, subscriptions: SubscriptionService, streaming: Category,
                            bank: Account) -> None:
        created = _netflix(subscriptions, streaming, bank, notes=" family plan ")

        assert created.amount == Money.of("150") and created.frequency is Frequency.MONTHLY
        assert created.anchor_day == 20 and created.is_active and created.notes == "family plan"
        assert subscriptions.get(created.id) == created
        assert subscriptions.list() == [created]

    def test_examples_and_monthly_total(
        self, subscriptions: SubscriptionService, streaming: Category
    ) -> None:
        for name, amount in (("Netflix", "150"), ("Spotify", "70"), ("Internet", "300")):
            subscriptions.create(name, amount=amount, frequency="monthly",
                                 next_payment_date=date(2026, 7, 1), category_id=streaming.id)

        assert subscriptions.statistics().monthly_total == Money.of("520")

    def test_update(self, subscriptions: SubscriptionService, streaming: Category,
                    categories: CategoryService) -> None:
        created = _netflix(subscriptions, streaming)
        tv = categories.create("TV", CategoryKind.EXPENSE)

        updated = subscriptions.update(
            created.id, name="Netflix Premium", amount="190", frequency=Frequency.YEARLY,
            next_payment_date=date(2026, 8, 31), category_id=tv.id, account_id=None, notes="",
        )

        assert (updated.name, updated.amount, updated.frequency) == (
            "Netflix Premium", Money.of("190"), Frequency.YEARLY
        )
        assert updated.anchor_day == 31 and updated.category_id == tv.id

    def test_update_keeping_the_date_keeps_the_billing_day(
        self, subscriptions: SubscriptionService, streaming: Category, bank: Account
    ) -> None:
        created = _netflix(subscriptions, streaming, bank, next_payment_date=date(2026, 5, 31))
        subscriptions.skip_payment(created.id, date(2026, 5, 31))  # next: 30 Jun, anchor 31

        updated = subscriptions.update(
            created.id, name="Netflix", amount="160", frequency=Frequency.MONTHLY,
            next_payment_date=date(2026, 6, 30), category_id=streaming.id, account_id=bank.id,
            notes="",
        )

        assert updated.anchor_day == 31  # still billed on the last day of long months

    def test_delete_keeps_recorded_expenses(
        self, subscriptions: SubscriptionService, transactions: TransactionService,
        streaming: Category, bank: Account,
    ) -> None:
        created = _netflix(subscriptions, streaming, bank, next_payment_date=TODAY)
        subscriptions.record_payment(created.id, TODAY)

        subscriptions.delete(created.id)

        with pytest.raises(NotFoundError):
            subscriptions.get(created.id)
        assert len(transactions.list()) == 1  # real money movements are never deleted

    @pytest.mark.parametrize(
        ("overrides", "field"),
        [
            ({"amount": "0"}, "amount"),
            ({"amount": 150.0}, "amount"),
            ({"frequency": "fortnightly"}, "frequency"),
            ({"category_id": 999}, "category_id"),
            ({"account_id": 999}, "account_id"),
            ({"next_payment_date": date(2024, 1, 1)}, "next_payment_date"),
        ],
    )
    def test_invalid(self, subscriptions: SubscriptionService, streaming: Category,
                     overrides: dict[str, object], field: str) -> None:
        with pytest.raises(ValidationError) as info:
            _netflix(subscriptions, streaming, **overrides)
        assert info.value.field == field
        assert subscriptions.list() == []

    def test_income_category_rejected(self, subscriptions: SubscriptionService,
                                      salary: Category) -> None:
        with pytest.raises(ValidationError, match="income category"):
            subscriptions.create("X", amount="1", frequency="monthly",
                                 next_payment_date=TODAY, category_id=salary.id)

    def test_duplicate_names(self, subscriptions: SubscriptionService, streaming: Category) -> None:
        _netflix(subscriptions, streaming)
        with pytest.raises(ConflictError):
            subscriptions.create(" NETFLIX", amount="1", frequency="monthly",
                                 next_payment_date=TODAY, category_id=streaming.id)

    def test_category_in_use_cannot_be_deleted(
        self, subscriptions: SubscriptionService, categories: CategoryService,
        streaming: Category,
    ) -> None:
        _netflix(subscriptions, streaming)
        with pytest.raises(ConflictError, match="subscription"):
            categories.delete(streaming.id)

    def test_deleting_the_default_account_clears_it(
        self, subscriptions: SubscriptionService, accounts: AccountService, streaming: Category
    ) -> None:
        wallet = accounts.create("Wallet")
        created = _netflix(subscriptions, streaming, wallet)

        accounts.delete(wallet.id)

        assert subscriptions.get(created.id).account_id is None


class TestActive:
    def test_paused_subscriptions_are_left_out(
        self, subscriptions: SubscriptionService, streaming: Category
    ) -> None:
        netflix = _netflix(subscriptions, streaming)
        subscriptions.create("Gym", amount="300", frequency="monthly",
                             next_payment_date=date(2026, 6, 25), category_id=streaming.id)

        paused = subscriptions.set_active(netflix.id, False)

        stats = subscriptions.statistics()
        assert not paused.is_active
        assert stats.monthly_total == Money.of("300") and stats.inactive_count == 1
        assert [p.subscription.name for p in subscriptions.upcoming()] == ["Gym"]
        assert subscriptions.set_active(netflix.id, True).is_active

    def test_paused_payments_cannot_be_confirmed(
        self, subscriptions: SubscriptionService, streaming: Category, bank: Account
    ) -> None:
        netflix = _netflix(subscriptions, streaming, bank, next_payment_date=TODAY)
        subscriptions.set_active(netflix.id, False)

        with pytest.raises(ValidationError, match="paused"):
            subscriptions.record_payment(netflix.id, TODAY)

    def test_flag_must_be_boolean(self, subscriptions: SubscriptionService,
                                  streaming: Category) -> None:
        netflix = _netflix(subscriptions, streaming)
        with pytest.raises(ValidationError):
            subscriptions.set_active(netflix.id, "no")  # type: ignore[arg-type]


class TestPayments:
    def test_record_creates_one_expense_and_advances(
        self, subscriptions: SubscriptionService, transactions: TransactionService,
        balances: BalanceService, streaming: Category, bank: Account,
    ) -> None:
        netflix = _netflix(subscriptions, streaming, bank, next_payment_date=date(2026, 6, 10))

        transaction = subscriptions.record_payment(netflix.id, date(2026, 6, 10))

        assert transaction.type is TransactionType.EXPENSE
        assert (transaction.amount, transaction.occurred_on) == (Money.of("150"), date(2026, 6, 10))
        assert transaction.category_id == streaming.id and transaction.description == "Netflix"
        assert balances.balance(bank.id) == Money.of("4850")
        assert subscriptions.get(netflix.id).next_payment_date == date(2026, 7, 10)
        [payment] = subscriptions.payments(netflix.id)
        assert (payment.status, payment.transaction_id) == (PaymentStatus.PAID, transaction.id)

    def test_duplicate_payment_is_impossible(
        self, subscriptions: SubscriptionService, transactions: TransactionService,
        streaming: Category, bank: Account,
    ) -> None:
        netflix = _netflix(subscriptions, streaming, bank, next_payment_date=date(2026, 6, 10))
        subscriptions.record_payment(netflix.id, date(2026, 6, 10))

        with pytest.raises(ConflictError, match="already been confirmed"):
            subscriptions.record_payment(netflix.id, date(2026, 6, 10))
        with pytest.raises(ConflictError, match="already been confirmed"):
            subscriptions.skip_payment(netflix.id, date(2026, 6, 10))

        assert len(transactions.list(TransactionFilter(category_id=streaming.id))) == 1

    def test_database_also_rejects_duplicate_due_dates(
        self, subscriptions: SubscriptionService, database: Database, streaming: Category,
        bank: Account,
    ) -> None:
        netflix = _netflix(subscriptions, streaming, bank, next_payment_date=TODAY)
        subscriptions.skip_payment(netflix.id, TODAY)

        with pytest.raises(IntegrityError), database.engine.begin() as conn:
            conn.exec_driver_sql(
                "INSERT INTO subscription_payments (subscription_id, due_date, status) "
                "VALUES (?, ?, 'paid')", (netflix.id, TODAY.isoformat()),
            )

    def test_only_the_next_due_date_can_be_confirmed(
        self, subscriptions: SubscriptionService, streaming: Category, bank: Account
    ) -> None:
        netflix = _netflix(subscriptions, streaming, bank, next_payment_date=date(2026, 5, 20))

        with pytest.raises(ConflictError, match="2026-05-20"):
            subscriptions.record_payment(netflix.id, date(2026, 6, 20))  # skipping May

    def test_cannot_confirm_far_in_advance(
        self, subscriptions: SubscriptionService, streaming: Category, bank: Account
    ) -> None:
        netflix = _netflix(subscriptions, streaming, bank, next_payment_date=date(2026, 6, 23))

        with pytest.raises(ValidationError, match="7 days early"):
            subscriptions.record_payment(netflix.id, date(2026, 6, 23))

    def test_early_payment_is_dated_today(
        self, subscriptions: SubscriptionService, streaming: Category, bank: Account
    ) -> None:
        netflix = _netflix(subscriptions, streaming, bank, next_payment_date=date(2026, 6, 20))

        transaction = subscriptions.record_payment(netflix.id, date(2026, 6, 20))

        assert transaction.occurred_on == TODAY

    def test_overrides_and_catching_up(
        self, subscriptions: SubscriptionService, streaming: Category, bank: Account,
        accounts: AccountService,
    ) -> None:
        cash = accounts.create("Cash", opening_balance="500", opening_date=OPENING_DATE)
        netflix = _netflix(subscriptions, streaming, bank, next_payment_date=date(2026, 4, 20))

        first = subscriptions.record_payment(netflix.id, date(2026, 4, 20), account_id=cash.id,
                                             amount="165.50", paid_on=date(2026, 4, 22))
        subscriptions.skip_payment(netflix.id, date(2026, 5, 20))

        assert (first.account_id, first.amount, first.occurred_on) == (
            cash.id, Money.of("165.50"), date(2026, 4, 22)
        )
        assert subscriptions.get(netflix.id).next_payment_date == date(2026, 6, 20)
        assert [p.status for p in subscriptions.payments(netflix.id)] == [
            PaymentStatus.SKIPPED, PaymentStatus.PAID
        ]

    def test_account_is_needed(self, subscriptions: SubscriptionService,
                               streaming: Category) -> None:
        netflix = _netflix(subscriptions, streaming, next_payment_date=TODAY)
        with pytest.raises(ValidationError) as info:
            subscriptions.record_payment(netflix.id, TODAY)
        assert info.value.field == "account_id"

    def test_failed_payment_changes_nothing(
        self, subscriptions: SubscriptionService, transactions: TransactionService,
        streaming: Category, bank: Account,
    ) -> None:
        netflix = _netflix(subscriptions, streaming, bank, next_payment_date=TODAY)

        with pytest.raises(ValidationError):
            subscriptions.record_payment(netflix.id, TODAY, amount="0")

        assert transactions.list() == []
        assert subscriptions.payments(netflix.id) == []
        assert subscriptions.get(netflix.id).next_payment_date == TODAY

    def test_month_end_schedule_after_payments(
        self, subscriptions: SubscriptionService, streaming: Category, bank: Account
    ) -> None:
        rent = subscriptions.create("Storage", amount="200", frequency="monthly",
                                    next_payment_date=date(2026, 1, 31), category_id=streaming.id,
                                    account_id=bank.id)
        for due in (date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)):
            subscriptions.skip_payment(rent.id, due)

        assert subscriptions.get(rent.id).next_payment_date == date(2026, 4, 30)

    def test_deleting_the_expense_keeps_the_confirmation(
        self, subscriptions: SubscriptionService, transactions: TransactionService,
        streaming: Category, bank: Account,
    ) -> None:
        netflix = _netflix(subscriptions, streaming, bank, next_payment_date=TODAY)
        transaction = subscriptions.record_payment(netflix.id, TODAY)

        transactions.delete(transaction.id)

        [payment] = subscriptions.payments(netflix.id)
        assert payment.status is PaymentStatus.PAID and payment.transaction_id is None
