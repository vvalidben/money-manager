"""Internal key/value bookkeeping about the database file itself."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from money_manager.persistence.base import Base


class AppMetadata(Base):
    __tablename__ = "app_metadata"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255))

    def __repr__(self) -> str:
        return f"AppMetadata(key={self.key!r}, value={self.value!r})"
