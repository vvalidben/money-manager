"""User preferences as key/value pairs (values are JSON text).

Never used for secrets: API keys live in the operating system's credential
store, not in the database file.
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from money_manager.persistence.base import Base, TimestampMixin


class SettingModel(TimestampMixin, Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"SettingModel(key={self.key!r})"
