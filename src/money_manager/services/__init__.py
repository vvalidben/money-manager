"""Application services: use cases that coordinate domain rules and persistence.

The UI talks only to services, never to the database directly. Each public
method runs in its own database transaction (all or nothing) and returns
immutable domain records, never ORM objects.
"""

from money_manager.services.account_service import AccountService
from money_manager.services.ai_service import AIService, PreparedRequest
from money_manager.services.allocation_service import (
    AllocationService,
    ConsistencyIssue,
    ConsistencyReport,
)
from money_manager.services.allocation_transfer_service import AllocationTransferService
from money_manager.services.analysis_service import FinancialAnalysisService
from money_manager.services.balance_service import BalanceService
from money_manager.services.category_service import CategoryService
from money_manager.services.data_service import DataService
from money_manager.services.container import AppServices
from money_manager.services.dashboard_service import DashboardService
from money_manager.services.goal_service import GoalService
from money_manager.services.investment_service import InvestmentService
from money_manager.services.settings_service import SettingsService
from money_manager.services.statistics_service import StatisticsService
from money_manager.services.subscription_service import SubscriptionService
from money_manager.services.transaction_service import TransactionService

__all__ = [
    "AIService",
    "AccountService",
    "AllocationService",
    "AllocationTransferService",
    "AppServices",
    "BalanceService",
    "CategoryService",
    "ConsistencyIssue",
    "ConsistencyReport",
    "DashboardService",
    "DataService",
    "FinancialAnalysisService",
    "GoalService",
    "InvestmentService",
    "PreparedRequest",
    "SettingsService",
    "StatisticsService",
    "SubscriptionService",
    "TransactionService",
]
