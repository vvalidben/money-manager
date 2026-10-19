"""Data access objects. Each repository wraps one session and one table."""

from money_manager.persistence.repositories.account_repository import AccountRepository
from money_manager.persistence.repositories.account_transfer_repository import (
    AccountTransferRepository,
)
from money_manager.persistence.repositories.ai_insight_repository import AIInsightRepository
from money_manager.persistence.repositories.allocation_repository import AllocationRepository
from money_manager.persistence.repositories.allocation_transfer_repository import (
    AllocationTransferRepository,
)
from money_manager.persistence.repositories.budget_repository import BudgetRepository
from money_manager.persistence.repositories.category_repository import CategoryRepository
from money_manager.persistence.repositories.category_rule_repository import (
    CategoryRuleRepository,
)
from money_manager.persistence.repositories.goal_repository import GoalRepository
from money_manager.persistence.repositories.investment_repository import InvestmentRepository
from money_manager.persistence.repositories.recurring_repository import RecurringRepository
from money_manager.persistence.repositories.setting_repository import SettingRepository
from money_manager.persistence.repositories.subscription_repository import (
    SubscriptionRepository,
)
from money_manager.persistence.repositories.transaction_repository import TransactionRepository

__all__ = [
    "AIInsightRepository",
    "AccountRepository",
    "AccountTransferRepository",
    "AllocationRepository",
    "AllocationTransferRepository",
    "BudgetRepository",
    "CategoryRepository",
    "CategoryRuleRepository",
    "GoalRepository",
    "InvestmentRepository",
    "RecurringRepository",
    "SettingRepository",
    "SubscriptionRepository",
    "TransactionRepository",
]
