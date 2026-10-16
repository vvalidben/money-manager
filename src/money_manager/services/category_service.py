"""Category use cases. Categories are entirely user-defined."""

import logging

from money_manager.core.errors import ConflictError, NotFoundError, ValidationError
from money_manager.domain.entities import Category
from money_manager.domain.enums import CategoryKind, parse_category_kind
from money_manager.domain.validation import (
    MAX_CATEGORY_NAME_LENGTH,
    clean_name,
    is_record_id,
    normalize_name,
)
from money_manager.persistence.database import Database
from money_manager.persistence.mappers import category_to_domain
from money_manager.persistence.models import CategoryModel
from money_manager.persistence.repositories import (
    CategoryRepository,
    SubscriptionRepository,
    TransactionRepository,
)

logger = logging.getLogger(__name__)


class CategoryService:
    def __init__(self, database: Database) -> None:
        self._database = database

    def create(self, name: str, kind: CategoryKind | str) -> Category:
        category_kind = parse_category_kind(kind)
        clean = clean_name(name, field="name", max_length=MAX_CATEGORY_NAME_LENGTH)
        with self._database.session() as session:
            repository = CategoryRepository(session)
            _ensure_name_available(repository, category_kind, clean)
            model = repository.add(
                CategoryModel(
                    name=clean,
                    normalized_name=normalize_name(clean),
                    kind=category_kind.value,
                    is_archived=False,
                )
            )
            category = category_to_domain(model)
        logger.info("Created category %s", category.id)
        return category

    def get(self, category_id: int) -> Category:
        with self._database.session() as session:
            return category_to_domain(_require(CategoryRepository(session), category_id))

    def list(
        self, kind: CategoryKind | str | None = None, *, include_archived: bool = False
    ) -> list[Category]:
        category_kind = None if kind is None else parse_category_kind(kind)
        with self._database.session() as session:
            models = CategoryRepository(session).list(category_kind, include_archived)
            return [category_to_domain(m) for m in models]

    def rename(self, category_id: int, name: str) -> Category:
        clean = clean_name(name, field="name", max_length=MAX_CATEGORY_NAME_LENGTH)
        with self._database.session() as session:
            repository = CategoryRepository(session)
            model = _require(repository, category_id)
            _ensure_name_available(repository, CategoryKind(model.kind), clean, exclude_id=model.id)
            model.name = clean
            model.normalized_name = normalize_name(clean)
            session.flush()
            return category_to_domain(model)

    def archive(self, category_id: int) -> Category:
        """Hide a category from new transactions; existing ones keep it."""
        return self._set_archived(category_id, True)

    def restore(self, category_id: int) -> Category:
        return self._set_archived(category_id, False)

    def set_investment(self, category_id: int, is_investment: bool) -> Category:
        """Mark an expense category as investing (counted as saving, not spending)."""
        if not isinstance(is_investment, bool):
            raise ValidationError("Choose yes or no.", "is_investment")
        with self._database.session() as session:
            model = _require(CategoryRepository(session), category_id)
            if is_investment and model.kind != CategoryKind.EXPENSE.value:
                raise ValidationError(
                    "Only expense categories can be investment categories.", "is_investment"
                )
            model.is_investment = is_investment
            session.flush()
            category = category_to_domain(model)
        logger.info("Category %s investment flag set to %s", category_id, is_investment)
        return category

    def delete(self, category_id: int) -> None:
        """Delete a category that no transaction uses (archive it otherwise)."""
        with self._database.session() as session:
            repository = CategoryRepository(session)
            model = _require(repository, category_id)
            if TransactionRepository(session).exists_for_category(model.id):
                raise ConflictError(
                    f"The category '{model.name}' is used by transactions; archive it instead."
                )
            if SubscriptionRepository(session).exists_for_category(model.id):
                raise ConflictError(
                    f"The category '{model.name}' is used by a subscription; change the "
                    "subscription's category first."
                )
            repository.delete(model)
        logger.info("Deleted category %s", category_id)

    def _set_archived(self, category_id: int, archived: bool) -> Category:
        with self._database.session() as session:
            model = _require(CategoryRepository(session), category_id)
            model.is_archived = archived
            session.flush()
            return category_to_domain(model)


def _ensure_name_available(
    repository: CategoryRepository, kind: CategoryKind, name: str, exclude_id: int | None = None
) -> None:
    existing = repository.get_by_normalized_name(kind, normalize_name(name))
    if existing is not None and existing.id != exclude_id:
        raise ConflictError(f"An {kind.value} category named '{existing.name}' already exists.")


def _require(repository: CategoryRepository, category_id: int) -> CategoryModel:
    model = repository.get(category_id) if is_record_id(category_id) else None
    if model is None:
        raise NotFoundError(f"Category {category_id!r} does not exist.")
    return model
