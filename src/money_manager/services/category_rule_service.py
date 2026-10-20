"""Category rules: learn them from corrections, manage them, look up a category."""

import logging
from dataclasses import dataclass

from money_manager.core.errors import NotFoundError, ValidationError
from money_manager.domain.categorize import (
    CategoryRule,
    clean_keyword,
    learn_keyword,
    match,
)
from money_manager.domain.enums import CategoryKind
from money_manager.domain.validation import validate_id
from money_manager.persistence.database import Database
from money_manager.persistence.models import CategoryRuleModel
from money_manager.persistence.repositories import CategoryRepository, CategoryRuleRepository
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RuleEntry:
    rule: CategoryRule
    category_name: str


def _to_domain(model: CategoryRuleModel) -> CategoryRule:
    return CategoryRule(model.id, model.keyword, model.category_id, CategoryKind(model.kind))


class CategoryRuleService:
    def __init__(self, database: Database) -> None:
        self._database = database

    def rules(self) -> list[CategoryRule]:
        with self._database.session() as session:
            return [_to_domain(m) for m in CategoryRuleRepository(session).list()]

    def entries(self) -> list[RuleEntry]:
        """Every rule with its category's name, by keyword."""
        with self._database.session() as session:
            names = {c.id: c.name for c in CategoryRepository(session).list(include_archived=True)}
            return [RuleEntry(_to_domain(m), names.get(m.category_id, "?"))
                    for m in CategoryRuleRepository(session).list()]

    def category_for(self, description: str, kind: CategoryKind) -> int | None:
        rule = match(description, kind, self.rules())
        return None if rule is None else rule.category_id

    def learn(self, description: str, category_id: int) -> CategoryRule | None:
        """Remember the description's keyword for this category (None: no usable word)."""
        keyword = learn_keyword(description)
        if keyword is None:
            return None
        return self._save(keyword, category_id)

    def add(self, keyword: str, category_id: int) -> CategoryRule:
        cleaned = clean_keyword(keyword)
        if cleaned is None:
            raise ValidationError(tr("Enter a keyword of 2 to 60 letters or digits."), "keyword")
        return self._save(cleaned, category_id)

    def remove(self, rule_id: int) -> None:
        with self._database.session() as session:
            rules = CategoryRuleRepository(session)
            model = rules.get(validate_id(rule_id, "rule_id"))
            if model is None:
                raise NotFoundError(tr("Rule {0!r} does not exist.", rule_id))
            rules.delete(model)
        logger.info("Removed category rule %s", rule_id)

    def _save(self, keyword: str, category_id: int) -> CategoryRule:
        with self._database.session() as session:
            category = CategoryRepository(session).get(validate_id(category_id, "category_id"))
            if category is None:
                raise ValidationError(tr("The selected category does not exist."), "category_id")
            rules = CategoryRuleRepository(session)
            model = rules.find(keyword, category.kind)
            if model is None:
                model = rules.add(CategoryRuleModel(keyword=keyword, kind=category.kind,
                                                    category_id=category.id))
            else:
                model.category_id = category.id
                session.flush()
            rule = _to_domain(model)
        logger.info("Category rule %s saved", rule.id)
        return rule
