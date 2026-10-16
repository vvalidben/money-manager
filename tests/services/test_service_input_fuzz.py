"""Every public service method, called with hostile values in each parameter.

A method may succeed or reject the input with a user-facing error
(``MoneyManagerError``). A crash (TypeError, OverflowError, …) or a
``DatabaseError`` (a constraint the validation should have caught) is a bug.
"""

from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any


from money_manager.ai.settings import AIMode, AISettings
from money_manager.core.errors import DatabaseError, MoneyManagerError
from money_manager.domain.entities import TransactionDraft, TransactionFilter, TransactionQuery
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.periods import DateRange
from money_manager.services import AppServices
from tests.services.support import TODAY

HOSTILE: list[Any] = [
    None, "", "   ", "abc", -1, 0, True, 1.5, 10**30, -(10**30), "1e400", "NaN", "Infinity",
    "-0", "0.001", Decimal("NaN"), date(1800, 1, 1), date(2999, 1, 1), datetime(2026, 1, 1),
    "2026-01-01", [], {}, "x" * 5000, "a\x00b", "  Ünïcödé 💶  ",
]


class World:
    def __init__(self, s: AppServices) -> None:
        self.s = s
        self.bank = s.accounts.create("Bank", opening_balance="5000", opening_date=date(2026, 1, 1))
        self.salary = s.categories.create("Salary", CategoryKind.INCOME)
        self.food = s.categories.create("Food", CategoryKind.EXPENSE)
        self.pot = s.allocations.create("Pot", initial_amount="100")
        self.tx = s.transactions.create(TransactionDraft(
            self.bank.id, TransactionType.EXPENSE, "10", TODAY, self.food.id, "x"))
        self.goal = s.goals.create_manual("Trip", target="1000")
        self.backed = s.goals.create_with_new_allocation("Car", target="1000", initial_amount="10")
        self.sub = s.subscriptions.create("Net", amount="10", frequency="monthly",
                                          next_payment_date=TODAY, category_id=self.food.id,
                                          account_id=self.bank.id)
        self.fund = s.investments.create("Fund", "etf")
        self.entry = s.investments.add_withdrawal(self.fund.investment.id, "5", TODAY)
        self.value = s.investments.set_value(self.fund.investment.id, "5", TODAY)
        self.transfer = s.transfers.transfer(from_allocation_id=None,
                                             to_allocation_id=self.pot.id, amount="1")
        # Local AI (no network is used to prepare a request), so ai.prepare runs fully.
        s.ai.save_settings(AISettings(AIMode.LOCAL, local_model="llama3.2"))

    def draft(self, **changes: Any) -> TransactionDraft:
        return replace(TransactionDraft(self.bank.id, TransactionType.EXPENSE, "10", TODAY,
                                        self.food.id, "desc", "notes"), **changes)

    def calls(self) -> list[tuple[str, Callable[..., Any], dict[str, Any]]]:
        s, fund = self.s, self.fund.investment.id
        return [
            ("accounts.create", s.accounts.create,
             {"name": "New", "opening_balance": "1", "opening_date": TODAY}),
            ("accounts.update", lambda account_id, **kw: s.accounts.update(account_id, **kw),
             {"account_id": self.bank.id, "name": "Bank", "opening_balance": "1",
              "opening_date": date(2026, 1, 1)}),
            ("accounts.get", s.accounts.get, {"account_id": self.bank.id}),
            ("categories.create", s.categories.create, {"name": "C", "kind": "expense"}),
            ("categories.rename", s.categories.rename,
             {"category_id": self.food.id, "name": "Food"}),
            ("categories.set_investment", s.categories.set_investment,
             {"category_id": self.food.id, "is_investment": False}),
            ("transactions.create", lambda **kw: s.transactions.create(self.draft(**kw)),
             {"account_id": self.bank.id, "type": "expense", "amount": "1",
              "occurred_on": TODAY, "category_id": self.food.id, "description": "d",
              "notes": "n", "allocation_id": None}),
            ("transactions.update",
             lambda transaction_id, **kw: s.transactions.update(transaction_id, self.draft(**kw)),
             {"transaction_id": self.tx.id, "amount": "2"}),
            ("transactions.get", s.transactions.get, {"transaction_id": self.tx.id}),
            ("transactions.search",
             lambda search, start, end, limit, offset: s.transactions.search(TransactionQuery(
                 filters=TransactionFilter(search=search, start=start, end=end),
                 limit=limit, offset=offset)),
             {"search": "a", "start": None, "end": None, "limit": 10, "offset": 0}),
            ("balances.breakdown", s.balances.breakdown,
             {"account_id": self.bank.id, "as_of": TODAY}),
            ("balances.reconcile", lambda account_id, actual_balance, on:
             s.balances.reconcile(account_id, actual_balance, on=on),
             {"account_id": self.bank.id, "actual_balance": "4000", "on": TODAY}),
            ("allocations.create", s.allocations.create, {"name": "P2", "initial_amount": "1"}),
            ("allocations.rename", s.allocations.rename,
             {"allocation_id": self.pot.id, "name": "Pot"}),
            ("allocations.balance", s.allocations.balance, {"allocation_id": self.pot.id}),
            ("transfers.transfer", s.transfers.transfer,
             {"from_allocation_id": None, "to_allocation_id": self.pot.id, "amount": "1",
              "on": TODAY, "note": "n"}),
            ("transfers.get", s.transfers.get, {"transfer_id": self.transfer.id}),
            ("goals.create_manual", s.goals.create_manual,
             {"name": "G", "target": "10", "current": "1", "deadline": None, "description": ""}),
            ("goals.create_with_new_allocation", s.goals.create_with_new_allocation,
             {"name": "G2", "target": "10", "deadline": None, "description": "",
              "initial_amount": "1"}),
            ("goals.contribute", s.goals.contribute,
             {"goal_id": self.backed.goal.id, "amount": "1"}),
            ("goals.withdraw", s.goals.withdraw, {"goal_id": self.backed.goal.id, "amount": "1"}),
            ("goals.set_manual_amount", s.goals.set_manual_amount,
             {"goal_id": self.goal.goal.id, "amount": "1"}),
            ("goals.get", s.goals.get, {"goal_id": self.goal.goal.id}),
            ("subscriptions.create", s.subscriptions.create,
             {"name": "S", "amount": "1", "frequency": "weekly", "next_payment_date": TODAY,
              "category_id": self.food.id, "account_id": None, "notes": "", "is_active": True}),
            ("subscriptions.record_payment", s.subscriptions.record_payment,
             {"subscription_id": self.sub.id, "due_date": TODAY, "account_id": self.bank.id,
              "amount": None, "paid_on": None}),
            ("subscriptions.skip_payment", s.subscriptions.skip_payment,
             {"subscription_id": self.sub.id, "due_date": TODAY}),
            ("subscriptions.set_active", s.subscriptions.set_active,
             {"subscription_id": self.sub.id, "active": True}),
            ("investments.create", s.investments.create, {"name": "I", "kind": "gold", "notes": ""}),
            ("investments.add_contribution", s.investments.add_contribution,
             {"investment_id": fund, "amount": "1", "on": TODAY, "note": "",
              "account_id": None, "category_id": None}),
            ("investments.add_withdrawal", s.investments.add_withdrawal,
             {"investment_id": fund, "amount": "1", "on": TODAY, "note": ""}),
            ("investments.set_value", s.investments.set_value,
             {"investment_id": fund, "value": "1", "on": TODAY, "note": ""}),
            ("investments.set_archived", s.investments.set_archived,
             {"investment_id": fund, "archived": False}),
            ("statistics.custom_range", s.statistics.custom_range,
             {"start": date(2026, 1, 1), "end": TODAY}),
            ("analysis.analyze", s.analysis.analyze,
             {"period": DateRange(date(2026, 1, 1), TODAY)}),
            ("statistics.report", s.statistics.report,
             {"period": DateRange(date(2026, 1, 1), TODAY)}),
            # Deletes and look-ups: the valid value is an id that does not exist.
            ("accounts.delete", s.accounts.delete, {"account_id": 999_999}),
            ("categories.delete", s.categories.delete, {"category_id": 999_999}),
            ("categories.archive", s.categories.archive, {"category_id": 999_999}),
            ("transactions.delete", s.transactions.delete, {"transaction_id": 999_999}),
            ("allocations.archive", s.allocations.archive, {"allocation_id": 999_999}),
            ("allocations.delete", s.allocations.delete, {"allocation_id": 999_999}),
            ("transfers.undo", s.transfers.undo, {"transfer_id": 999_999}),
            ("goals.delete", s.goals.delete, {"goal_id": 999_999, "release_money": True}),
            ("subscriptions.delete", s.subscriptions.delete, {"subscription_id": 999_999}),
            ("subscriptions.payments", s.subscriptions.payments, {"subscription_id": 999_999}),
            ("investments.delete", s.investments.delete, {"investment_id": 999_999}),
            ("investments.delete_entry", s.investments.delete_entry, {"entry_id": 999_999}),
            ("investments.delete_valuation", s.investments.delete_valuation,
             {"valuation_id": 999_999}),
            ("ai.insight", s.ai.insight, {"insight_id": 999_999}),
            ("ai.delete_insight", s.ai.delete_insight, {"insight_id": 999_999}),
            ("ai.set_mode", s.ai.set_mode, {"mode": "off"}),
            ("ai.prepare", s.ai.prepare, {"question": "Why?", "kind": None, "period": None}),
            ("settings.set_currency", s.settings.set_currency, {"code": "MAD"}),
            ("ai.save_settings", lambda **kw: s.ai.save_settings(AISettings().with_changes(**kw)),
             {"mode": "off", "local_url": "http://localhost:11434", "local_model": "m",
              "online_model": "claude-opus-5", "timeout_seconds": 60}),
            ("ai.save_api_key", s.ai.save_api_key, {"text": "sk-ant-valid-key-000000"}),
            ("data.reset", s.data.reset, {"confirmation": "no"}),
            ("data.read_backup", s.data.read_backup, {"path": Path("missing-backup.json")}),
            ("data.import_backup", s.data.import_backup, {"path": Path("missing-backup.json")}),
        ]


def test_hostile_inputs_never_crash(app_services: AppServices) -> None:
    world = World(app_services)
    problems: list[str] = []
    for label, method, valid in world.calls():
        for parameter in valid:
            for value in HOSTILE:
                arguments = {**valid, parameter: value}
                try:
                    method(**arguments)
                except DatabaseError as exc:
                    problems.append(f"{label}({parameter}={value!r:.40}): DatabaseError {exc}")
                except MoneyManagerError:
                    pass
                except Exception as exc:  # noqa: BLE001
                    problems.append(f"{label}({parameter}={value!r:.40}): "
                                    f"{type(exc).__name__}: {str(exc)[:80]}")
    assert problems == [], "\n".join(problems)
