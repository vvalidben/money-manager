"""Monthly budgets per expense category: set, remove and track this month's spending."""

import logging
from collections.abc import Callable
from datetime import date

from money_manager.core.errors import NotFoundError, ValidationError
from money_manager.domain.budgets import Budget, BudgetStatus, BudgetSummary
from money_manager.domain.enums import CategoryKind
from money_manager.domain.money import DEFAULT_CURRENCY, AmountInput, Money
from money_manager.domain.periods import month_end, month_start
from money_manager.domain.validation import positive_amount, validate_id
from money_manager.persistence.database import Database
from money_manager.persistence.models import BudgetModel
from money_manager.persistence.repositories import BudgetRepository, CategoryRepository

logger = logging.getLogger(__name__)


class BudgetService:
    def __init__(self, database: Database, *, today: Callable[[], date] = date.today,
                 base_currency: str = DEFAULT_CURRENCY) -> None:
        self._database = database
        self._today = today
        self._currency = base_currency

    def overview(self, month: date | None = None) -> BudgetSummary:
        """Every budget with the month's spending (this month: so far), most used first."""
        today = self._today()
        if month is not None and month_start(month) < month_start(today):
            today = month_end(month)  # a past month, measured on its last day
        with self._database.session() as session:
            budgets = BudgetRepository(session)
            models = budgets.list()
            spent = budgets.spent_minor([m.category_id for m in models], month_start(today), today)
            names = {c.id: c.name for c in CategoryRepository(session).list(include_archived=True)}
        statuses = [
            BudgetStatus(self._to_domain(model), names.get(model.category_id, "?"),
                         Money.from_minor_units(spent.get(model.category_id, 0), self._currency),
                         today)
            for model in models
        ]
        statuses.sort(key=lambda s: (-s.ratio, s.category_name.casefold()))
        return BudgetSummary(tuple(statuses), self._currency)

    def set(self, category_id: int, amount: AmountInput) -> Budget:
        """Create the category's budget, or change its monthly limit."""
        category_id = validate_id(category_id, "category_id")
        limit = Money.of(positive_amount(amount, "amount"), self._currency)
        with self._database.session() as session:
            category = CategoryRepository(session).get(category_id)
            if category is None:
                raise ValidationError("The selected category does not exist.", "category_id")
            if category.kind != CategoryKind.EXPENSE.value:
                raise ValidationError("Budgets are for expense categories.", "category_id")
            budgets = BudgetRepository(session)
            model = budgets.for_category(category_id)
            if model is None:
                if category.is_archived:
                    raise ValidationError(f"The category '{category.name}' is archived.",
                                          "category_id")
                model = budgets.add(BudgetModel(category_id=category_id,
                                                amount_minor=limit.minor_units))
            else:
                model.amount_minor = limit.minor_units
                session.flush()
            budget = self._to_domain(model)
        logger.info("Budget for category %s set", category_id)
        return budget

    def remove(self, category_id: int) -> None:
        with self._database.session() as session:
            budgets = BudgetRepository(session)
            model = budgets.for_category(validate_id(category_id, "category_id"))
            if model is None:
                raise NotFoundError("This category has no budget.")
            budgets.delete(model)
        logger.info("Budget for category %s removed", category_id)

    def _to_domain(self, model: BudgetModel) -> Budget:
        return Budget(model.id, model.category_id,
                      Money.from_minor_units(model.amount_minor, self._currency))
