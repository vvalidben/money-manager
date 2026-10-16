from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from money_manager.domain.enums import CategoryKind
from money_manager.persistence.models import CategoryModel


class CategoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, category_id: int) -> CategoryModel | None:
        return self._session.get(CategoryModel, category_id)

    def list(
        self, kind: CategoryKind | None = None, include_archived: bool = False
    ) -> Sequence[CategoryModel]:
        stmt = select(CategoryModel).order_by(CategoryModel.normalized_name, CategoryModel.id)
        if kind is not None:
            stmt = stmt.where(CategoryModel.kind == kind.value)
        if not include_archived:
            stmt = stmt.where(CategoryModel.is_archived.is_(False))
        return self._session.scalars(stmt).all()

    def get_by_normalized_name(
        self, kind: CategoryKind, normalized_name: str
    ) -> CategoryModel | None:
        stmt = select(CategoryModel).where(
            CategoryModel.kind == kind.value, CategoryModel.normalized_name == normalized_name
        )
        return self._session.scalars(stmt).one_or_none()

    def add(self, category: CategoryModel) -> CategoryModel:
        self._session.add(category)
        self._session.flush()
        return category

    def delete(self, category: CategoryModel) -> None:
        self._session.delete(category)
        self._session.flush()
