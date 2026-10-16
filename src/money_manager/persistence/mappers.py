"""Conversion from ORM rows to immutable domain records."""

from datetime import date

from money_manager.domain.entities import (
    Account,
    Allocation,
    AllocationTransfer,
    Category,
    Transaction,
)
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.goals import Goal
from money_manager.domain.insights import Insight, InsightKind
from money_manager.domain.investments import (
    EntryKind,
    Investment,
    InvestmentEntry,
    InvestmentKind,
    Valuation,
)
from money_manager.domain.money import Money
from money_manager.domain.periods import DateRange
from money_manager.domain.subscriptions import Frequency, Subscription
from money_manager.persistence.models import (
    AIInsightModel,
    AccountModel,
    AllocationModel,
    AllocationTransferModel,
    CategoryModel,
    GoalModel,
    InvestmentEntryModel,
    InvestmentModel,
    InvestmentValuationModel,
    SubscriptionModel,
    TransactionModel,
)


def account_to_domain(model: AccountModel) -> Account:
    return Account(
        id=model.id,
        name=model.name,
        currency=model.currency,
        opening_balance=Money.from_minor_units(model.opening_balance_minor, model.currency),
        opening_date=model.opening_date,
    )


def category_to_domain(model: CategoryModel) -> Category:
    return Category(
        id=model.id,
        name=model.name,
        kind=CategoryKind(model.kind),
        is_archived=model.is_archived,
        is_investment=model.is_investment,
    )


def transaction_to_domain(model: TransactionModel) -> Transaction:
    return Transaction(
        id=model.id,
        account_id=model.account_id,
        type=TransactionType(model.type),
        amount=Money.from_minor_units(model.amount_minor, model.currency),
        occurred_on=model.occurred_on,
        category_id=model.category_id,
        description=model.description,
        notes=model.notes,
        allocation_id=model.allocation_id,
    )


def allocation_to_domain(model: AllocationModel) -> Allocation:
    return Allocation(id=model.id, name=model.name, is_archived=model.is_archived)


def transfer_to_domain(model: AllocationTransferModel, currency: str) -> AllocationTransfer:
    """Allocations are kept in the single base currency, which is not stored per row."""
    return AllocationTransfer(
        id=model.id,
        from_allocation_id=model.from_allocation_id,
        to_allocation_id=model.to_allocation_id,
        amount=Money.from_minor_units(model.amount_minor, currency),
        occurred_on=model.occurred_on,
        note=model.note,
    )


def goal_to_domain(model: GoalModel, currency: str) -> Goal:
    """Goals are kept in the base currency, which is not stored per row."""
    return Goal(
        id=model.id,
        name=model.name,
        description=model.description,
        target=Money.from_minor_units(model.target_minor, currency),
        start_date=model.start_date,
        deadline=model.deadline,
        allocation_id=model.allocation_id,
        manual_amount=(
            None
            if model.manual_current_minor is None
            else Money.from_minor_units(model.manual_current_minor, currency)
        ),
    )


def subscription_to_domain(model: SubscriptionModel, currency: str) -> Subscription:
    """Subscriptions are kept in the base currency, which is not stored per row."""
    return Subscription(
        id=model.id,
        name=model.name,
        amount=Money.from_minor_units(model.amount_minor, currency),
        frequency=Frequency(model.frequency),
        next_payment_date=model.next_payment_date,
        anchor_day=model.anchor_day,
        category_id=model.category_id,
        account_id=model.account_id,
        is_active=model.is_active,
        notes=model.notes,
    )


def investment_to_domain(model: InvestmentModel) -> Investment:
    return Investment(
        id=model.id,
        name=model.name,
        kind=InvestmentKind(model.kind),
        notes=model.notes,
        is_archived=model.is_archived,
    )


def investment_entry_to_domain(
    model: InvestmentEntryModel, amount_minor: int, occurred_on: date, currency: str
) -> InvestmentEntry:
    """``amount_minor``/``occurred_on`` are resolved from the backing transaction if any."""
    return InvestmentEntry(
        id=model.id,
        investment_id=model.investment_id,
        kind=EntryKind(model.kind),
        amount=Money.from_minor_units(amount_minor, currency),
        occurred_on=occurred_on,
        note=model.note,
        transaction_id=model.transaction_id,
    )


def valuation_to_domain(model: InvestmentValuationModel, currency: str) -> Valuation:
    return Valuation(
        id=model.id,
        investment_id=model.investment_id,
        valued_on=model.valued_on,
        value=Money.from_minor_units(model.value_minor, currency),
        note=model.note,
    )


def insight_to_domain(model: AIInsightModel) -> Insight:
    return Insight(
        id=model.id,
        kind=InsightKind(model.kind),
        question=model.question,
        period=DateRange(model.period_start, model.period_end),
        provider=model.provider,
        model=model.model,
        is_online=model.is_online,
        answer=model.answer,
        context=model.context,
        truncated=model.truncated,
        created_at=model.created_at,
    )
