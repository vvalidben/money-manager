"""Investments on a real database, including their link to transactions."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from money_manager.core.errors import ConflictError, NotFoundError, ValidationError
from money_manager.domain.entities import Account, Category, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.investments import EntryKind, InvestmentKind
from money_manager.domain.money import Money
from money_manager.domain.periods import DateRange
from money_manager.persistence.database import Database
from money_manager.services import (
    AccountService,
    AllocationService,
    BalanceService,
    CategoryService,
    InvestmentService,
    StatisticsService,
    TransactionService,
)
from tests.services.support import OPENING_DATE, TODAY, fixed_today


@pytest.fixture
def investments(database: Database, transactions: TransactionService) -> InvestmentService:
    return InvestmentService(database, transactions, today=fixed_today)


@pytest.fixture
def bank(accounts: AccountService) -> Account:
    return accounts.create("Bank", opening_balance="10000", opening_date=OPENING_DATE)


@pytest.fixture
def stocks(categories: CategoryService) -> Category:
    category = categories.create("Investing", CategoryKind.EXPENSE)
    return categories.set_investment(category.id, True)


class TestCrud:
    def test_create_get_list(self, investments: InvestmentService) -> None:
        created = investments.create("  World ETF ", InvestmentKind.ETF, notes="Monthly DCA")

        assert (created.investment.name, created.investment.kind) == ("World ETF",
                                                                     InvestmentKind.ETF)
        assert created.net_invested == Money.zero() and created.current_value is None
        assert investments.get(created.investment.id) == created
        assert [p.investment.name for p in investments.list()] == ["World ETF"]

    @pytest.mark.parametrize("kind", ["stock", "etf", "crypto", "gold", "other"])
    def test_every_kind(self, investments: InvestmentService, kind: str) -> None:
        assert investments.create(f"Holding {kind}", kind).investment.kind is InvestmentKind(kind)

    def test_update(self, investments: InvestmentService) -> None:
        created = investments.create("BTC", "crypto")
        updated = investments.update(created.investment.id, name="Bitcoin", kind="crypto",
                                     notes="Cold wallet")
        assert (updated.investment.name, updated.investment.notes) == ("Bitcoin", "Cold wallet")

    def test_invalid_and_duplicates(self, investments: InvestmentService) -> None:
        investments.create("Gold coins", "gold")
        with pytest.raises(ConflictError):
            investments.create("GOLD COINS", "gold")
        with pytest.raises(ValidationError):
            investments.create("Bonds", "bond")
        with pytest.raises(ValidationError):
            investments.create(" ", "gold")

    def test_archive(self, investments: InvestmentService) -> None:
        created = investments.create("Old shares", "stock")
        investments.set_archived(created.investment.id, True)

        assert investments.list() == []
        assert len(investments.list(include_archived=True)) == 1
        with pytest.raises(ValidationError, match="archived"):
            investments.add_withdrawal(created.investment.id, "10", TODAY)

    def test_delete_keeps_real_expenses(
        self, investments: InvestmentService, transactions: TransactionService, bank: Account,
        stocks: Category,
    ) -> None:
        created = investments.create("ETF", "etf")
        investments.add_contribution(created.investment.id, "500", TODAY, account_id=bank.id,
                                     category_id=stocks.id)

        investments.delete(created.investment.id)

        with pytest.raises(NotFoundError):
            investments.get(created.investment.id)
        assert len(transactions.list()) == 1  # the money really left the account


class TestContributions:
    def test_external_contribution_does_not_touch_the_balance(
        self, investments: InvestmentService, balances: BalanceService, bank: Account
    ) -> None:
        created = investments.create("Gold", "gold")

        entry = investments.add_contribution(created.investment.id, "2500", date(2026, 3, 1),
                                             note="Bought before tracking")

        assert (entry.kind, entry.amount, entry.transaction_id) == (
            EntryKind.CONTRIBUTION, Money.of("2500"), None
        )
        assert investments.get(created.investment.id).net_invested == Money.of("2500")
        assert balances.total_balance() == Money.of("10000")

    def test_paid_from_account_creates_one_investment_expense(
        self, investments: InvestmentService, balances: BalanceService,
        transactions: TransactionService, bank: Account, stocks: Category,
    ) -> None:
        created = investments.create("World ETF", "etf")

        entry = investments.add_contribution(created.investment.id, "1000", date(2026, 6, 1),
                                             account_id=bank.id, category_id=stocks.id)

        [transaction] = transactions.list()
        assert entry.transaction_id == transaction.id
        assert (transaction.type, transaction.category_id, transaction.description) == (
            TransactionType.EXPENSE, stocks.id, "World ETF"
        )
        assert balances.total_balance() == Money.of("9000")
        assert investments.get(created.investment.id).contributed == Money.of("1000")

    def test_counts_as_investment_in_statistics(
        self, investments: InvestmentService, database: Database, bank: Account,
        stocks: Category, salary: Category, transactions: TransactionService,
    ) -> None:
        transactions.create(TransactionDraft(bank.id, TransactionType.INCOME, "5000",
                                             date(2026, 6, 1), salary.id))
        created = investments.create("World ETF", "etf")
        investments.add_contribution(created.investment.id, "1000", date(2026, 6, 2),
                                     account_id=bank.id, category_id=stocks.id)

        totals = StatisticsService(database, today=fixed_today).report(
            DateRange(date(2026, 6, 1), TODAY)).totals

        assert totals.investments == Money.of("1000")
        assert totals.investment_rate == Decimal("0.2000")
        assert totals.spending.is_zero()

    def test_paid_from_an_allocation(
        self, investments: InvestmentService, allocations: AllocationService, bank: Account,
        stocks: Category,
    ) -> None:
        pot = allocations.create("To invest", initial_amount="3000")
        created = investments.create("ETF", "etf")

        investments.add_contribution(created.investment.id, "1200", TODAY, account_id=bank.id,
                                     category_id=stocks.id, allocation_id=pot.id)

        assert allocations.balance(pot.id) == Money.of("1800")
        assert allocations.available() == Money.of("7000")  # unchanged: paid from the pot

    def test_category_must_be_an_investment_category(
        self, investments: InvestmentService, categories: CategoryService, bank: Account,
        transactions: TransactionService,
    ) -> None:
        food = categories.create("Food", CategoryKind.EXPENSE)
        created = investments.create("ETF", "etf")

        with pytest.raises(ValidationError, match="not an investment category"):
            investments.add_contribution(created.investment.id, "10", TODAY,
                                         account_id=bank.id, category_id=food.id)
        with pytest.raises(ValidationError) as info:
            investments.add_contribution(created.investment.id, "10", TODAY, account_id=bank.id)
        assert info.value.field == "category_id"
        assert transactions.list() == []

    @pytest.mark.parametrize(
        ("amount", "on", "field"),
        [("0", TODAY, "amount"), ("-5", TODAY, "amount"), (10.0, TODAY, "amount"),
         ("1.234", TODAY, "amount"), ("10", date(2026, 6, 16), "occurred_on")],
    )
    def test_invalid_contributions(self, investments: InvestmentService, amount: object,
                                   on: date, field: str) -> None:
        created = investments.create("ETF", "etf")
        with pytest.raises(ValidationError) as info:
            investments.add_contribution(created.investment.id, amount, on)  # type: ignore[arg-type]
        assert info.value.field == field
        assert investments.get(created.investment.id).entries == ()

    def test_linked_amount_follows_the_transaction(
        self, investments: InvestmentService, transactions: TransactionService, bank: Account,
        stocks: Category,
    ) -> None:
        created = investments.create("ETF", "etf")
        entry = investments.add_contribution(created.investment.id, "1000", date(2026, 6, 1),
                                             account_id=bank.id, category_id=stocks.id)
        assert entry.transaction_id is not None

        transactions.update(entry.transaction_id, TransactionDraft(
            bank.id, TransactionType.EXPENSE, "1250.50", date(2026, 6, 3), stocks.id))

        [updated] = investments.get(created.investment.id).entries
        assert (updated.amount, updated.occurred_on) == (Money.of("1250.50"), date(2026, 6, 3))

    def test_linked_expense_cannot_become_income(
        self, investments: InvestmentService, transactions: TransactionService, bank: Account,
        stocks: Category, salary: Category,
    ) -> None:
        created = investments.create("ETF", "etf")
        entry = investments.add_contribution(created.investment.id, "1000", TODAY,
                                             account_id=bank.id, category_id=stocks.id)
        assert entry.transaction_id is not None

        with pytest.raises(ValidationError, match="must stay an expense"):
            transactions.update(entry.transaction_id, TransactionDraft(
                bank.id, TransactionType.INCOME, "1000", TODAY, salary.id))

    def test_deleting_the_transaction_deletes_the_contribution(
        self, investments: InvestmentService, transactions: TransactionService, bank: Account,
        stocks: Category,
    ) -> None:
        created = investments.create("ETF", "etf")
        entry = investments.add_contribution(created.investment.id, "1000", TODAY,
                                             account_id=bank.id, category_id=stocks.id)
        assert entry.transaction_id is not None

        transactions.delete(entry.transaction_id)

        assert investments.get(created.investment.id).entries == ()

    def test_delete_entry(
        self, investments: InvestmentService, transactions: TransactionService,
        balances: BalanceService, bank: Account, stocks: Category,
    ) -> None:
        created = investments.create("ETF", "etf")
        external = investments.add_contribution(created.investment.id, "100", TODAY)
        linked = investments.add_contribution(created.investment.id, "400", TODAY,
                                              account_id=bank.id, category_id=stocks.id)

        investments.delete_entry(external.id)
        investments.delete_entry(linked.id)

        assert investments.get(created.investment.id).entries == ()
        assert transactions.list() == []  # the linked expense went with it
        assert balances.total_balance() == Money.of("10000")
        with pytest.raises(NotFoundError):
            investments.delete_entry(linked.id)

    def test_withdrawal(self, investments: InvestmentService, balances: BalanceService,
                        bank: Account) -> None:
        created = investments.create("Gold", "gold")
        investments.add_contribution(created.investment.id, "1000", date(2026, 1, 5))

        entry = investments.add_withdrawal(created.investment.id, "300", date(2026, 5, 1))

        assert entry.kind is EntryKind.WITHDRAWAL
        assert investments.get(created.investment.id).net_invested == Money.of("700")
        assert balances.total_balance() == Money.of("10000")

    def test_database_rejects_inconsistent_entries(
        self, investments: InvestmentService, database: Database
    ) -> None:
        created = investments.create("ETF", "etf")
        with pytest.raises(IntegrityError), database.engine.begin() as conn:
            conn.exec_driver_sql(
                "INSERT INTO investment_entries (investment_id, kind, amount_minor, occurred_on, "
                "note) VALUES (?, 'contribution', 0, '2026-06-01', '')",
                (created.investment.id,),
            )


class TestValues:
    def test_profit_and_return(self, investments: InvestmentService, bank: Account,
                               stocks: Category) -> None:
        created = investments.create("World ETF", "etf")
        investments.add_contribution(created.investment.id, "1000", date(2026, 1, 5),
                                     account_id=bank.id, category_id=stocks.id)
        investments.add_contribution(created.investment.id, "500", date(2026, 3, 5))

        investments.set_value(created.investment.id, "1650", date(2026, 6, 1))

        item = investments.get(created.investment.id)
        assert item.current_value == Money.of("1650")
        assert item.profit == Money.of("150")
        assert item.return_ratio == Decimal("0.1000")

    def test_same_day_value_is_replaced(self, investments: InvestmentService) -> None:
        created = investments.create("Gold", "gold")
        investments.set_value(created.investment.id, "100", TODAY)
        investments.set_value(created.investment.id, "120", TODAY, note="corrected")

        [valuation] = investments.get(created.investment.id).valuations
        assert (valuation.value, valuation.note) == (Money.of("120"), "corrected")

    def test_value_rules(self, investments: InvestmentService) -> None:
        created = investments.create("Gold", "gold")
        assert investments.set_value(created.investment.id, "0", TODAY).value == Money.zero()
        with pytest.raises(ValidationError):
            investments.set_value(created.investment.id, "-1", TODAY)
        with pytest.raises(ValidationError):
            investments.set_value(created.investment.id, "1", date(2026, 6, 16))

    def test_out_of_date_value_has_no_return(self, investments: InvestmentService) -> None:
        created = investments.create("ETF", "etf")
        investments.add_contribution(created.investment.id, "1000", date(2026, 1, 5))
        investments.set_value(created.investment.id, "1100", date(2026, 2, 1))
        investments.add_contribution(created.investment.id, "500", date(2026, 3, 1))

        item = investments.get(created.investment.id)
        assert item.current_value == Money.of("1100") and item.profit is None

    def test_delete_valuation(self, investments: InvestmentService) -> None:
        created = investments.create("Gold", "gold")
        valuation = investments.set_value(created.investment.id, "100", TODAY)

        investments.delete_valuation(valuation.id)

        assert investments.get(created.investment.id).current_value is None
        with pytest.raises(NotFoundError):
            investments.delete_valuation(valuation.id)


def test_summary_net_worth(investments: InvestmentService, bank: Account,
                           stocks: Category) -> None:
    etf = investments.create("ETF", "etf")
    investments.add_contribution(etf.investment.id, "2000", date(2026, 6, 1), account_id=bank.id,
                                 category_id=stocks.id)
    investments.set_value(etf.investment.id, "2300", TODAY)
    gold = investments.create("Gold", "gold")
    investments.add_contribution(gold.investment.id, "1000", date(2026, 1, 1))

    summary = investments.summary()

    assert summary.total_balance == Money.of("8000")
    assert summary.total_value == Money.of("2300")  # gold was never valued
    assert summary.net_worth == Money.of("10300")
    assert summary.total_profit == Money.of("300")
    assert summary.return_ratio == Decimal("0.1500")
    assert summary.net_invested == Money.of("3000")
