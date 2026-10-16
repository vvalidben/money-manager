from datetime import date

from sqlalchemy import CheckConstraint, Date, String
from sqlalchemy.orm import Mapped, mapped_column

from money_manager.domain.validation import MAX_ACCOUNT_NAME_LENGTH
from money_manager.persistence.base import Base, TimestampMixin


class AccountModel(TimestampMixin, Base):
    """A place where money is held. Its balance is derived, never stored."""

    __tablename__ = "accounts"
    __table_args__ = (CheckConstraint("length(currency) = 3", name="currency_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(MAX_ACCOUNT_NAME_LENGTH))
    normalized_name: Mapped[str] = mapped_column(String(MAX_ACCOUNT_NAME_LENGTH), unique=True)
    currency: Mapped[str] = mapped_column(String(3))
    # Signed integer minor units (centimes); may be negative for an overdrawn start.
    opening_balance_minor: Mapped[int]
    opening_date: Mapped[date] = mapped_column(Date)
