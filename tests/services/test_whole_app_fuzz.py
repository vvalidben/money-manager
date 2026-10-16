"""Randomised whole-application check.

Long random sequences of real user operations (accounts, transactions and
edits, reconciliations, transfers, allocations, goals, subscriptions,
investments, categories, backup round trips). After every step:

* a rejected operation (``MoneyManagerError``) left every table unchanged;
* every service reports the same total balance as an independent SQL sum;
* statistics, search and SQL agree on income and expenses;
* allocations are never negative and Available + Σ allocations = total;
* backed goals equal their allocation; linked investment entries and
  subscription payments point at matching transactions;
* the database passes its integrity and foreign-key checks.

Any other exception is a bug and fails the test.
"""

import random
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select

from money_manager.core.errors import MoneyManagerError
from money_manager.domain.entities import TransactionDraft, TransactionQuery
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import sum_money
from money_manager.domain.periods import DateRange
from money_manager.persistence.database import Database
from money_manager.services import AppServices
from money_manager.services.data_service import RESET_CONFIRMATION, data_tables
from tests.services.support import TODAY

START = date(2026, 1, 1)
SIGNED = ("CASE WHEN type IN ('income', 'adjustment_in') THEN amount_minor "
          "ELSE -amount_minor END")


def snapshot(database: Database) -> dict[str, list[tuple[Any, ...]]]:
    with database.session() as session:
        return {t.name: [tuple(r) for r in session.execute(
            select(t).order_by(*t.primary_key.columns))] for t in data_tables()}


def scalar(database: Database, sql: str) -> int:
    with database.engine.connect() as connection:
        return int(connection.exec_driver_sql(sql).scalar() or 0)


class Fuzzer:
    def __init__(self, s: AppServices, database: Database, rng: random.Random,
                 tmp_path: Path) -> None:
        self.s, self.db, self.rng, self.tmp = s, database, rng, tmp_path
        self.salary = s.categories.create("Salary", CategoryKind.INCOME)
        self.food = s.categories.create("Food", CategoryKind.EXPENSE)
        self.rent = s.categories.create("Rent", CategoryKind.EXPENSE)
        self.stocks = s.categories.create("Stocks", CategoryKind.EXPENSE)
        s.categories.set_investment(self.stocks.id, True)
        s.accounts.create("Bank", opening_balance="5000", opening_date=START)
        self.operations: dict[str, Callable[[], object]] = {
            name.removeprefix("op_"): getattr(self, name)
            for name in dir(self) if name.startswith("op_")
        }

    # ----------------------------------------------------------- helpers

    def amount(self, high: int = 300_000) -> str:
        cents = self.rng.randint(1, high)
        return f"{cents // 100}.{cents % 100:02d}"

    def day(self, first: date = START, last: date = TODAY) -> date:
        return date.fromordinal(self.rng.randint(first.toordinal(), last.toordinal()))

    def pick(self, items: list[Any]) -> Any:
        return self.rng.choice(items) if items else None

    def allocation_or_none(self) -> int | None:
        active = self.s.allocations.list()
        return None if not active or self.rng.random() < 0.5 else self.rng.choice(active).id

    def draft(self) -> TransactionDraft:
        account = self.pick(self.s.accounts.list())
        is_income = self.rng.random() < 0.35
        category = self.salary if is_income else self.rng.choice([self.food, self.rent])
        return TransactionDraft(
            account.id, TransactionType.INCOME if is_income else TransactionType.EXPENSE,
            self.amount(), self.day(account.opening_date), category.id,
            description=self.rng.choice(["Market", "Salary", "Taxi", "Rent", ""]),
            allocation_id=self.allocation_or_none())

    # -------------------------------------------------------- operations

    def op_account(self) -> None:
        if len(self.s.accounts.list()) < 3:
            self.s.accounts.create(f"Account {self.rng.randint(1, 10_000)}",
                                   opening_balance=self.amount(), opening_date=self.day(START))

    def op_account_edit(self) -> None:
        account = self.pick(self.s.accounts.list())
        self.s.accounts.update(account.id, name=account.name,
                               opening_balance=f"-{self.amount()}" if self.rng.random() < 0.2
                               else self.amount(),
                               opening_date=self.day(START, date(2026, 3, 1)))

    def op_income_or_expense(self) -> None:
        self.s.transactions.create(self.draft())

    op_income_or_expense_2 = op_income_or_expense

    def op_edit(self) -> None:
        existing = self.s.transactions.list()
        if existing:
            self.s.transactions.update(self.rng.choice(existing).id, self.draft())

    def op_delete(self) -> None:
        existing = self.s.transactions.list()
        if existing:
            self.s.transactions.delete(self.rng.choice(existing).id)

    def op_reconcile(self) -> None:
        account = self.pick(self.s.accounts.list())
        self.s.balances.reconcile(account.id, self.amount(2_000_000),
                                  on=self.day(account.opening_date))

    def op_transfer(self) -> None:
        endpoints = [None, *[a.id for a in self.s.allocations.list()]]
        if len(endpoints) > 1:
            source, destination = self.rng.sample(endpoints, 2)
            self.s.transfers.transfer(from_allocation_id=source, to_allocation_id=destination,
                                      amount=self.amount(), on=self.day())

    def op_undo(self) -> None:
        history = self.s.transfers.list()
        if history:
            self.s.transfers.undo(self.rng.choice(history).id)

    def op_allocation(self) -> None:
        self.s.allocations.create(f"Pot {self.rng.randint(1, 10_000)}",
                                  initial_amount=self.amount(50_000))

    def op_allocation_archive(self) -> None:
        pot = self.pick(self.s.allocations.list(include_archived=True))
        if pot is not None:
            if pot.is_archived:
                self.s.allocations.restore(pot.id)
            else:
                self.s.allocations.archive(pot.id)

    def op_goal(self) -> None:
        if self.rng.random() < 0.5:
            self.s.goals.create_with_new_allocation(
                f"Goal {self.rng.randint(1, 10_000)}", target=self.amount(),
                initial_amount=self.amount(20_000))
        else:
            self.s.goals.create_manual(f"Manual {self.rng.randint(1, 10_000)}",
                                       target=self.amount(), current=self.amount(10_000))

    def op_goal_money(self) -> None:
        goal = self.pick(self.s.goals.list())
        if goal is None:
            return
        action = self.rng.choice(["contribute", "withdraw", "manual", "delete"])
        if action == "contribute":
            self.s.goals.contribute(goal.goal.id, self.amount(30_000))
        elif action == "withdraw":
            self.s.goals.withdraw(goal.goal.id, self.amount(30_000))
        elif action == "manual":
            self.s.goals.set_manual_amount(goal.goal.id, self.amount(30_000))
        else:
            self.s.goals.delete(goal.goal.id, release_money=self.rng.random() < 0.5)

    def op_subscription(self) -> None:
        self.s.subscriptions.create(
            f"Sub {self.rng.randint(1, 10_000)}", amount=self.amount(20_000),
            frequency=self.rng.choice(["weekly", "monthly", "quarterly", "yearly"]),
            next_payment_date=self.day(TODAY - timedelta(days=60), TODAY + timedelta(days=3)),
            category_id=self.rng.choice([self.food, self.rent]).id,
            account_id=self.pick([None, *[a.id for a in self.s.accounts.list()]]))

    def op_subscription_payment(self) -> None:
        sub = self.pick(self.s.subscriptions.list())
        if sub is None:
            return
        action = self.rng.choice(["record", "record", "skip", "pause"])
        if action == "record":
            account = self.pick(self.s.accounts.list())
            self.s.subscriptions.record_payment(sub.id, sub.next_payment_date,
                                                account_id=account.id)
        elif action == "skip":
            self.s.subscriptions.skip_payment(sub.id, sub.next_payment_date)
        else:
            self.s.subscriptions.set_active(sub.id, not sub.is_active)

    def op_investment(self) -> None:
        position = self.pick(self.s.investments.list())
        if position is None or self.rng.random() < 0.15:
            self.s.investments.create(f"Fund {self.rng.randint(1, 10_000)}",
                                      self.rng.choice(["etf", "stock", "gold"]))
            return
        investment_id = position.investment.id
        action = self.rng.choice(["paid", "external", "withdraw", "value", "delete_entry",
                                  "delete_value"])
        if action == "paid":
            account = self.pick(self.s.accounts.list())
            self.s.investments.add_contribution(investment_id, self.amount(), self.day(
                account.opening_date), account_id=account.id, category_id=self.stocks.id)
        elif action == "external":
            self.s.investments.add_contribution(investment_id, self.amount(), self.day())
        elif action == "withdraw":
            self.s.investments.add_withdrawal(investment_id, self.amount(), self.day())
        elif action == "value":
            self.s.investments.set_value(investment_id, self.amount(), self.day())
        elif action == "delete_entry" and position.entries:
            self.s.investments.delete_entry(self.rng.choice(position.entries).id)
        elif action == "delete_value" and position.valuations:
            self.s.investments.delete_valuation(self.rng.choice(position.valuations).id)

    def op_category(self) -> None:
        category = self.rng.choice([self.food, self.rent])
        if self.s.categories.get(category.id).is_archived:
            self.s.categories.restore(category.id)
        elif self.rng.random() < 0.3:
            self.s.categories.archive(category.id)

    def op_roundtrip(self) -> None:
        before = snapshot(self.db)
        path = self.tmp / f"backup-{self.rng.randint(1, 10**9)}.json"
        self.s.data.export_backup(path)
        self.s.data.reset(RESET_CONFIRMATION)
        self.s.data.import_backup(path)
        assert snapshot(self.db) == before, "backup round trip changed data"

    # ------------------------------------------------------------ checks

    def check(self) -> None:
        s, db = self.s, self.db
        total = scalar(db, "SELECT sum(opening_balance_minor) FROM accounts") + scalar(
            db, f"SELECT sum({SIGNED}) FROM transactions")
        income = scalar(db, "SELECT sum(amount_minor) FROM transactions WHERE type='income'")
        expenses = scalar(db, "SELECT sum(amount_minor) FROM transactions WHERE type='expense'")

        assert s.balances.total_balance().minor_units == total
        summary = s.allocations.summary()
        assert summary.total_balance.minor_units == total
        assert all(not row.balance.is_negative() for row in summary.allocations)
        assert summary.available + sum_money(r.balance for r in summary.allocations) == (
            summary.total_balance)
        assert s.dashboard.overview().total_balance.minor_units == total
        assert s.analysis.analyze().current_balance.minor_units == total

        report = s.statistics.report(DateRange(START, TODAY))
        assert report.balance.closing.minor_units == total
        assert report.totals.income.minor_units == income
        assert report.totals.expenses.minor_units == expenses
        page = s.transactions.search(TransactionQuery(limit=1))
        assert (page.income.minor_units, page.expenses.minor_units) == (income, expenses)

        for goal in s.goals.list():
            if goal.goal.allocation_id is not None:
                assert goal.current == s.allocations.balance(goal.goal.allocation_id)
        for position in s.investments.list(include_archived=True):
            for entry in position.entries:
                if entry.transaction_id is not None:
                    linked = s.transactions.get(entry.transaction_id)
                    assert linked.type is TransactionType.EXPENSE
                    assert linked.amount == entry.amount and linked.occurred_on == entry.occurred_on
        for sub in s.subscriptions.list():
            for payment in s.subscriptions.payments(sub.id):
                if payment.transaction_id is not None:
                    s.transactions.get(payment.transaction_id)  # raises if missing

        issues = {issue.code for issue in s.allocations.check_consistency().issues}
        assert issues <= {"over_allocated"}, issues
        with db.engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
            assert connection.exec_driver_sql("PRAGMA integrity_check").scalar() == "ok"

    def run(self, steps: int) -> dict[str, int]:
        counts: dict[str, int] = {}
        names = sorted(self.operations)
        for _ in range(steps):
            name = self.rng.choice(names)
            before = snapshot(self.db)
            try:
                self.operations[name]()
                counts[name] = counts.get(name, 0) + 1
            except MoneyManagerError:
                counts["rejected"] = counts.get("rejected", 0) + 1
                assert snapshot(self.db) == before, f"rejected '{name}' changed data"
            self.check()
        return counts


@pytest.mark.parametrize("seed", [101, 202, 303, 404])
def test_random_operations_keep_every_figure_consistent(
    seed: int, app_services: AppServices, database: Database, tmp_path: Path,
) -> None:
    counts = Fuzzer(app_services, database, random.Random(seed), tmp_path).run(220)
    assert counts.get("rejected", 0) < 220 * 0.8  # the fuzzer really exercises the app
    assert len(counts) >= 12
