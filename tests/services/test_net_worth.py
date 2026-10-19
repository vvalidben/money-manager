"""Net worth over time: balances at each month end plus known investment values."""

from datetime import date

from money_manager.domain.entities import TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.investments import Valuation, value_on
from money_manager.domain.money import Money
from money_manager.services import AppServices


def test_value_on_takes_the_latest_known_value() -> None:
    valuations = [Valuation(1, 7, date(2026, 3, 10), Money.of("100"), ""),
                  Valuation(2, 7, date(2026, 5, 2), Money.of("130"), "")]
    assert value_on(valuations, date(2026, 3, 9)) is None
    assert value_on(valuations, date(2026, 4, 30)) == Money.of("100")
    assert value_on(valuations, date(2026, 5, 2)) == Money.of("130")


def test_no_accounts_no_history(app_services: AppServices) -> None:
    assert app_services.net_worth.history() == []


def test_month_by_month(app_services: AppServices) -> None:
    bank = app_services.accounts.create("Bank", opening_balance="1000",
                                        opening_date=date(2026, 3, 5))
    salary = app_services.categories.create("Salary", CategoryKind.INCOME)
    app_services.transactions.create(TransactionDraft(bank.id, TransactionType.INCOME, "500",
                                                      date(2026, 4, 30), salary.id))
    app_services.transactions.create(TransactionDraft(bank.id, TransactionType.INCOME, "250",
                                                      date(2026, 6, 15), salary.id))
    etf = app_services.investments.create("ETF", "etf")
    app_services.investments.set_value(etf.investment.id, "2000", date(2026, 5, 20))
    gold = app_services.investments.create("Gold", "other")
    app_services.investments.set_value(gold.investment.id, "300", date(2026, 4, 1))
    app_services.investments.set_archived(gold.investment.id, True)  # no longer counted

    points = app_services.net_worth.history()

    assert [(p.month, p.on) for p in points] == [
        (date(2026, 3, 1), date(2026, 3, 31)), (date(2026, 4, 1), date(2026, 4, 30)),
        (date(2026, 5, 1), date(2026, 5, 31)), (date(2026, 6, 1), date(2026, 6, 15))]
    assert [p.balance for p in points] == [Money.of(v) for v in ("1000", "1500", "1500", "1750")]
    assert [p.investments for p in points] == [Money.of(v) for v in ("0", "0", "2000", "2000")]
    assert points[-1].net_worth == app_services.investments.summary().net_worth


def test_at_most_the_last_months(app_services: AppServices) -> None:
    app_services.accounts.create("Bank", opening_balance="10", opening_date=date(2024, 1, 1))
    points = app_services.net_worth.history()
    assert len(points) == 12
    assert (points[0].month, points[-1].month) == (date(2025, 7, 1), date(2026, 6, 1))
    assert len(app_services.net_worth.history(3)) == 3
