"""Pure validation rules for accounts, categories, transactions and allocations."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from money_manager.core.errors import ValidationError
from money_manager.domain.entities import Account, Allocation, Category, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType, parse_transaction_type
from money_manager.domain.money import Money, parse_amount, validate_currency
from money_manager.domain.investments import InvestmentKind
from money_manager.domain.subscriptions import Frequency
from money_manager.core.i18n import tr

EARLIEST_ALLOWED_DATE = date(1900, 1, 1)
MAX_ACCOUNT_NAME_LENGTH = 60
MAX_CATEGORY_NAME_LENGTH = 40
MAX_ALLOCATION_NAME_LENGTH = 40
MAX_DESCRIPTION_LENGTH = 200
MAX_NOTES_LENGTH = 2000
MAX_TRANSFER_NOTE_LENGTH = 200
MAX_GOAL_NAME_LENGTH = 60
MAX_GOAL_DESCRIPTION_LENGTH = 500

# Names that would be confused with the derived "Available" pool.
RESERVED_ALLOCATION_NAMES = frozenset({"available", "unallocated"})


def clean_name(value: object, *, field: str, max_length: int) -> str:
    """Trim and collapse internal whitespace; reject empty or overlong names."""
    if not isinstance(value, str):
        raise ValidationError(tr("Name must be text."), field)
    name = " ".join(value.split())
    if not name:
        raise ValidationError(tr("Name cannot be empty."), field)
    if len(name) > max_length:
        raise ValidationError(tr("Name cannot be longer than {0} characters.", max_length), field)
    return name


def normalize_name(name: str) -> str:
    """Key used for case-insensitive uniqueness checks."""
    return " ".join(name.split()).casefold()


def clean_text(value: object, *, field: str, max_length: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError(tr("Must be text."), field)
    text = value.strip()
    if len(text) > max_length:
        raise ValidationError(tr("Cannot be longer than {0} characters.", max_length), field)
    return text


def validate_date(value: object, *, field: str, today: date) -> date:
    """Accept a calendar date between 1900-01-01 and today."""
    # datetime is a subclass of date; a time component is not meaningful here.
    if isinstance(value, datetime) or not isinstance(value, date):
        raise ValidationError(tr("Enter a valid calendar date."), field)
    if value < EARLIEST_ALLOWED_DATE:
        raise ValidationError(
            tr("Date cannot be before {0}.", EARLIEST_ALLOWED_DATE.isoformat()), field
        )
    if value > today:
        raise ValidationError(tr("Date cannot be in the future."), field)
    return value


# Record ids are SQLite rowids: positive signed 64-bit integers.
MAX_RECORD_ID = 2**63 - 1


def is_record_id(value: object) -> bool:
    """A possible record id; anything else cannot exist (and must not reach SQLite,
    which raises OverflowError for integers outside 64 bits)."""
    return (isinstance(value, int) and not isinstance(value, bool)
            and 1 <= value <= MAX_RECORD_ID)


def validate_id(value: object, field: str) -> int:
    if not is_record_id(value):
        raise ValidationError(tr("Invalid reference."), field)
    assert isinstance(value, int)
    return value


def positive_amount(value: object, field: str = "amount", hint: str = "") -> Decimal:
    amount = parse_amount(value, field)
    if amount <= 0:
        raise ValidationError(tr("Amount must be greater than zero{0}.", hint), field)
    return amount


@dataclass(frozen=True, slots=True)
class ValidAccount:
    name: str
    currency: str
    opening_balance: Money
    opening_date: date


def validate_account(
    *,
    name: object,
    opening_balance: object,
    opening_date: object,
    currency: object,
    today: date,
) -> ValidAccount:
    clean_currency = validate_currency(currency)
    return ValidAccount(
        name=clean_name(name, field="name", max_length=MAX_ACCOUNT_NAME_LENGTH),
        currency=clean_currency,
        # Any sign is allowed: an account may start overdrawn.
        opening_balance=Money(parse_amount(opening_balance, "opening_balance"), clean_currency),
        opening_date=validate_date(opening_date, field="opening_date", today=today),
    )


@dataclass(frozen=True, slots=True)
class ValidTransaction:
    account_id: int
    type: TransactionType
    amount: Money
    occurred_on: date
    category_id: int | None
    description: str
    notes: str
    allocation_id: int | None = None


def validate_transaction(
    draft: TransactionDraft,
    *,
    account: Account,
    category: Category | None,
    today: date,
    keep_archived_category_id: int | None = None,
    allocation: Allocation | None = None,
    keep_archived_allocation_id: int | None = None,
) -> ValidTransaction:
    """Check a draft against its (already loaded) account, category and allocation.

    The ``keep_archived_*`` arguments let an edited transaction keep an
    archived category or allocation it already had. Whether the allocation
    holds enough money is checked by the service, which knows the balances.
    """
    transaction_type = parse_transaction_type(draft.type)
    amount = Money(
        positive_amount(
            draft.amount, hint=tr(" (the transaction type decides whether money comes in or goes out)")
        ),
        account.currency,
    )

    occurred_on = validate_date(draft.occurred_on, field="occurred_on", today=today)
    if occurred_on < account.opening_date:
        raise ValidationError(
            tr("Date cannot be before the account's opening date ({0}); the opening "
               "balance already includes earlier activity.", account.opening_date.isoformat()),
            "occurred_on",
        )

    expected_kind = transaction_type.category_kind
    if expected_kind is None:
        if draft.category_id is not None:
            raise ValidationError(tr("Balance adjustments do not use a category."), "category_id")
        category_id = None
    else:
        if category is None:
            raise ValidationError(tr("Choose a category."), "category_id")
        if category.kind is not expected_kind:
            raise ValidationError(
                tr("'{0}' is an {1} category and cannot be used for an {2} transaction.", category.name, tr(category.kind.value), transaction_type.label),
                "category_id",
            )
        if category.is_archived and category.id != keep_archived_category_id:
            raise ValidationError(tr("The category '{0}' is archived.", category.name), "category_id")
        category_id = category.id

    if draft.allocation_id is None:
        allocation_id = None
    else:
        if transaction_type.is_adjustment:
            raise ValidationError(
                tr("Balance adjustments always affect Available money and cannot use an "
                "allocation."),
                "allocation_id",
            )
        if allocation is None:
            raise ValidationError(tr("The selected allocation does not exist."), "allocation_id")
        if allocation.is_archived and allocation.id != keep_archived_allocation_id:
            raise ValidationError(
                tr("The allocation '{0}' is archived.", allocation.name), "allocation_id"
            )
        allocation_id = allocation.id

    return ValidTransaction(
        account_id=account.id,
        type=transaction_type,
        amount=amount,
        occurred_on=occurred_on,
        category_id=category_id,
        description=clean_text(
            draft.description, field="description", max_length=MAX_DESCRIPTION_LENGTH
        ),
        notes=clean_text(draft.notes, field="notes", max_length=MAX_NOTES_LENGTH),
        allocation_id=allocation_id,
    )


MAX_SUBSCRIPTION_NAME_LENGTH = 60
MAX_INVESTMENT_NAME_LENGTH = 60
MAX_INVESTMENT_NOTE_LENGTH = 200
SUBSCRIPTION_PAST_LIMIT_DAYS = 366
SUBSCRIPTION_FUTURE_LIMIT_YEARS = 10


@dataclass(frozen=True, slots=True)
class ValidSubscription:
    name: str
    amount: Money
    frequency: Frequency
    next_payment_date: date
    anchor_day: int
    category_id: int
    notes: str


def validate_subscription(
    *,
    name: object,
    amount: object,
    frequency: object,
    next_payment_date: object,
    category: Category | None,
    notes: object,
    currency: str,
    today: date,
    keep_archived_category_id: int | None = None,
) -> ValidSubscription:
    """Validate subscription fields (the category is loaded by the service)."""
    if isinstance(frequency, Frequency):
        clean_frequency = frequency
    else:
        try:
            clean_frequency = Frequency(str(frequency).strip().lower())
        except ValueError:
            allowed = ", ".join(f.value for f in Frequency)
            raise ValidationError(
                tr("Invalid frequency {0!r}; expected one of: {1}.", frequency, allowed), "frequency"
            ) from None

    if isinstance(next_payment_date, datetime) or not isinstance(next_payment_date, date):
        raise ValidationError(tr("Enter a valid calendar date."), "next_payment_date")
    if (today - next_payment_date).days > SUBSCRIPTION_PAST_LIMIT_DAYS:
        raise ValidationError(
            tr("The next payment date cannot be more than a year in the past."), "next_payment_date"
        )
    if next_payment_date.year > today.year + SUBSCRIPTION_FUTURE_LIMIT_YEARS:
        raise ValidationError(
            tr("The next payment date must be within {0} years.", SUBSCRIPTION_FUTURE_LIMIT_YEARS),
            "next_payment_date",
        )

    if category is None:
        raise ValidationError(tr("Choose a category."), "category_id")
    if category.kind is not CategoryKind.EXPENSE:
        raise ValidationError(
            tr("'{0}' is an income category; subscriptions need an expense category.", category.name),
            "category_id",
        )
    if category.is_archived and category.id != keep_archived_category_id:
        raise ValidationError(tr("The category '{0}' is archived.", category.name), "category_id")

    return ValidSubscription(
        name=clean_name(name, field="name", max_length=MAX_SUBSCRIPTION_NAME_LENGTH),
        amount=Money(positive_amount(amount), currency),
        frequency=clean_frequency,
        next_payment_date=next_payment_date,
        anchor_day=next_payment_date.day,
        category_id=category.id,
        notes=clean_text(notes, field="notes", max_length=MAX_NOTES_LENGTH),
    )


@dataclass(frozen=True, slots=True)
class ValidInvestment:
    name: str
    kind: InvestmentKind
    notes: str


def validate_investment(*, name: object, kind: object, notes: object) -> ValidInvestment:
    if isinstance(kind, InvestmentKind):
        clean_kind = kind
    else:
        try:
            clean_kind = InvestmentKind(str(kind).strip().lower())
        except ValueError:
            allowed = ", ".join(k.value for k in InvestmentKind)
            raise ValidationError(
                tr("Invalid investment type {0!r}; expected one of: {1}.", kind, allowed), "kind"
            ) from None
    return ValidInvestment(
        name=clean_name(name, field="name", max_length=MAX_INVESTMENT_NAME_LENGTH),
        kind=clean_kind,
        notes=clean_text(notes, field="notes", max_length=MAX_NOTES_LENGTH),
    )


MAX_DEADLINE_YEARS = 100


@dataclass(frozen=True, slots=True)
class ValidGoal:
    name: str
    target: Money
    deadline: date | None
    description: str


def validate_goal(
    *,
    name: object,
    target: object,
    deadline: object,
    description: object,
    currency: str,
    today: date,
    current_deadline: date | None = None,
) -> ValidGoal:
    """Validate goal fields. ``current_deadline`` lets an edit keep a deadline that has passed."""
    clean_deadline: date | None = None
    if deadline is not None:
        if isinstance(deadline, datetime) or not isinstance(deadline, date):
            raise ValidationError(tr("Enter a valid calendar date."), "deadline")
        if deadline < today and deadline != current_deadline:
            raise ValidationError(tr("The deadline cannot be in the past."), "deadline")
        if deadline.year > today.year + MAX_DEADLINE_YEARS:
            raise ValidationError(
                tr("The deadline must be within {0} years.", MAX_DEADLINE_YEARS), "deadline"
            )
        clean_deadline = deadline
    return ValidGoal(
        name=clean_name(name, field="name", max_length=MAX_GOAL_NAME_LENGTH),
        target=Money(positive_amount(target, "target"), currency),
        deadline=clean_deadline,
        description=clean_text(
            description, field="description", max_length=MAX_GOAL_DESCRIPTION_LENGTH
        ),
    )


def non_negative_amount(value: object, field: str = "amount") -> Decimal:
    amount = parse_amount(value, field)
    if amount < 0:
        raise ValidationError(tr("The amount cannot be negative."), field)
    return amount


def validate_allocation_name(value: object) -> str:
    name = clean_name(value, field="name", max_length=MAX_ALLOCATION_NAME_LENGTH)
    if normalize_name(name) in RESERVED_ALLOCATION_NAMES:
        raise ValidationError(
            tr("'{0}' is reserved for money that is not allocated.", name), "name"
        )
    return name


@dataclass(frozen=True, slots=True)
class ValidTransfer:
    from_allocation_id: int | None
    to_allocation_id: int | None
    amount: Money
    occurred_on: date
    note: str


def validate_transfer(
    *,
    source: Allocation | None,
    destination: Allocation | None,
    amount: object,
    occurred_on: object,
    note: object,
    currency: str,
    today: date,
) -> ValidTransfer:
    """Validate a transfer whose endpoints are already loaded (None = Available).

    Whether the source holds enough money is checked by the service.
    """
    if source is None and destination is None:
        raise ValidationError(
            tr("Choose an allocation; moving money from Available to Available does nothing."),
            "to_allocation_id",
        )
    if source is not None and destination is not None and source.id == destination.id:
        raise ValidationError(
            tr("The source and destination must be different."), "to_allocation_id"
        )
    for allocation, field in ((source, "from_allocation_id"), (destination, "to_allocation_id")):
        if allocation is not None and allocation.is_archived:
            raise ValidationError(tr("The allocation '{0}' is archived.", allocation.name), field)

    return ValidTransfer(
        from_allocation_id=None if source is None else source.id,
        to_allocation_id=None if destination is None else destination.id,
        amount=Money(positive_amount(amount), currency),
        occurred_on=validate_date(occurred_on, field="occurred_on", today=today),
        note=clean_text(note, field="note", max_length=MAX_TRANSFER_NOTE_LENGTH),
    )
