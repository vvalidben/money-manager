"""ORM models. Importing this package registers every table on ``Base.metadata``."""

from money_manager.persistence.models.account import AccountModel
from money_manager.persistence.models.account_transfer import AccountTransferModel
from money_manager.persistence.models.ai_insight import AIInsightModel
from money_manager.persistence.models.allocation import AllocationModel
from money_manager.persistence.models.allocation_transfer import AllocationTransferModel
from money_manager.persistence.models.app_metadata import AppMetadata
from money_manager.persistence.models.budget import BudgetModel
from money_manager.persistence.models.category import CategoryModel
from money_manager.persistence.models.goal import GoalModel
from money_manager.persistence.models.investment import (
    InvestmentEntryModel,
    InvestmentModel,
    InvestmentValuationModel,
)
from money_manager.persistence.models.setting import SettingModel
from money_manager.persistence.models.subscription import (
    SubscriptionModel,
    SubscriptionPaymentModel,
)
from money_manager.persistence.models.transaction import TransactionModel

__all__ = [
    "AIInsightModel",
    "AccountModel",
    "AccountTransferModel",
    "AllocationModel",
    "AllocationTransferModel",
    "AppMetadata",
    "BudgetModel",
    "CategoryModel",
    "GoalModel",
    "InvestmentEntryModel",
    "InvestmentModel",
    "InvestmentValuationModel",
    "SettingModel",
    "SubscriptionModel",
    "SubscriptionPaymentModel",
    "TransactionModel",
]
