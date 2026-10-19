"""Wires every service to one database, clock and base currency.

The base currency comes from the stored setting (``SettingsService``) unless
given; changing it means building a new ``AppServices``.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Self

from money_manager.ai.secrets import SecretStore, default_secret_store
from money_manager.persistence.database import Database
from money_manager.services.account_service import AccountService
from money_manager.services.account_transfer_service import AccountTransferService
from money_manager.services.ai_service import AIService
from money_manager.services.allocation_service import AllocationService
from money_manager.services.analysis_service import FinancialAnalysisService
from money_manager.services.allocation_transfer_service import AllocationTransferService
from money_manager.services.balance_service import BalanceService
from money_manager.services.budget_service import BudgetService
from money_manager.services.category_rule_service import CategoryRuleService
from money_manager.services.category_service import CategoryService
from money_manager.services.data_service import DataService
from money_manager.services.dashboard_service import DashboardService
from money_manager.services.goal_service import GoalService
from money_manager.services.investment_service import InvestmentService
from money_manager.services.net_worth_service import NetWorthService
from money_manager.services.recurring_service import RecurringService
from money_manager.services.report_service import ReportService
from money_manager.services.settings_service import SettingsService
from money_manager.services.statement_import_service import StatementImportService
from money_manager.services.statistics_service import StatisticsService
from money_manager.services.subscription_service import SubscriptionService
from money_manager.services.transaction_service import TransactionService


@dataclass(frozen=True, slots=True)
class AppServices:
    accounts: AccountService
    categories: CategoryService
    transactions: TransactionService
    balances: BalanceService
    allocations: AllocationService
    transfers: AllocationTransferService
    account_transfers: AccountTransferService
    budgets: BudgetService
    statements: StatementImportService
    category_rules: CategoryRuleService
    dashboard: DashboardService
    statistics: StatisticsService
    goals: GoalService
    subscriptions: SubscriptionService
    investments: InvestmentService
    net_worth: NetWorthService
    reports: ReportService
    recurring: RecurringService
    analysis: FinancialAnalysisService
    ai: AIService
    settings: SettingsService
    data: DataService
    today: Callable[[], date]
    base_currency: str
    data_revision: Callable[[], int]

    def freshness(self) -> tuple[int, date]:
        """Changes whenever data is written or the date changes; pages that were
        already refreshed for the same value can skip recalculating."""
        return self.data_revision(), self.today()

    @classmethod
    def create(
        cls,
        database: Database,
        *,
        today: Callable[[], date] = date.today,
        base_currency: str | None = None,
        secret_store: SecretStore | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> Self:
        """``secret_store`` defaults to the Windows Credential Manager, ``environ`` to
        ``os.environ`` (for ANTHROPIC_API_KEY); tests pass isolated ones."""
        settings = SettingsService(database)
        base_currency = settings.currency() if base_currency is None else base_currency
        secrets = default_secret_store() if secret_store is None else secret_store
        analysis = FinancialAnalysisService(database, today=today, base_currency=base_currency)
        transactions = TransactionService(database, today=today, base_currency=base_currency)
        balances = BalanceService(database, transactions, today=today, base_currency=base_currency)
        rules = CategoryRuleService(database)
        investments = InvestmentService(database, transactions, today=today,
                                        base_currency=base_currency)
        accounts = AccountService(database, today=today, default_currency=base_currency)
        categories = CategoryService(database)
        budgets = BudgetService(database, today=today, base_currency=base_currency)
        statistics = StatisticsService(database, today=today, base_currency=base_currency)
        goals = GoalService(database, today=today, base_currency=base_currency)
        net_worth = NetWorthService(database, balances, investments, today=today,
                                    base_currency=base_currency)
        allocations = AllocationService(database, balances, today=today,
                                        base_currency=base_currency)
        return cls(
            accounts=accounts,
            categories=categories,
            transactions=transactions,
            balances=balances,
            allocations=allocations,
            transfers=AllocationTransferService(
                database, today=today, base_currency=base_currency
            ),
            account_transfers=AccountTransferService(database, transactions, today=today),
            budgets=budgets,
            statements=StatementImportService(database, transactions, rules, today=today),
            category_rules=rules,
            dashboard=DashboardService(database, today=today, base_currency=base_currency),
            statistics=statistics,
            goals=goals,
            subscriptions=SubscriptionService(
                database, transactions, today=today, base_currency=base_currency
            ),
            investments=investments,
            net_worth=net_worth,
            recurring=RecurringService(database, transactions, today=today,
                                       base_currency=base_currency),
            reports=ReportService(accounts=accounts, categories=categories,
                                  transactions=transactions, statistics=statistics,
                                  budgets=budgets, goals=goals, net_worth=net_worth,
                                  today=today, base_currency=base_currency),
            analysis=analysis,
            ai=AIService(database, analysis, secret_store=secrets, environ=environ),
            settings=settings,
            data=DataService(database, secret_store=secrets,
                             check_consistency=allocations.check_consistency),
            today=today,
            base_currency=base_currency,
            data_revision=lambda: database.revision,
        )
