from dataclasses import replace
from datetime import date

import pytest

from money_manager.core.errors import ValidationError
from money_manager.domain.entities import (
    Account,
    Category,
    Transaction,
    TransactionFilter,
    TransactionQuery,
)
from money_manager.domain.enums import CategoryKind, TransactionSort, TransactionType
from money_manager.domain.money import Money
from money_manager.services import CategoryService, TransactionService
from tests.services.support import AddTransaction


@pytest.fixture
def seeded(
    add: AddTransaction, categories: CategoryService, account: Account, salary: Category,
    food: Category,
) -> dict[str, Transaction]:
    rent = categories.create("Rent", CategoryKind.EXPENSE)
    return {
        "salary": add(TransactionType.INCOME, "12000", salary, on=date(2026, 5, 1),
                      description="Salary May"),
        "rent": add(TransactionType.EXPENSE, "4500", rent, on=date(2026, 5, 2),
                    description="Apartment", notes="paid 100% by transfer"),
        "groceries": add(TransactionType.EXPENSE, "312.40", food, on=date(2026, 5, 20),
                         description="Marjane groceries"),
        "snack": add(TransactionType.EXPENSE, "12.40", food, on=date(2026, 6, 1),
                     description="snack_bar"),
        "fix": add(TransactionType.ADJUSTMENT_IN, "3.10", on=date(2026, 6, 2),
                   description="Correction"),
    }


def _search(transactions: TransactionService, **filters: object) -> list[int]:
    page = transactions.search(TransactionQuery(filters=TransactionFilter(**filters)))  # type: ignore[arg-type]
    return [t.id for t in page.items]


def _ids(seeded: dict[str, Transaction], *names: str) -> list[int]:
    return [seeded[name].id for name in names]


class TestSearchText:
    def test_description_case_insensitive(
        self, transactions: TransactionService, seeded: dict[str, Transaction]
    ) -> None:
        assert _search(transactions, search="MARJANE") == _ids(seeded, "groceries")

    def test_category_name(self, transactions: TransactionService, seeded: dict[str, Transaction]) -> None:
        assert _search(transactions, search="food") == _ids(seeded, "snack", "groceries")

    def test_notes(self, transactions: TransactionService, seeded: dict[str, Transaction]) -> None:
        assert _search(transactions, search="transfer") == _ids(seeded, "rent")

    def test_like_wildcards_are_literal(
        self, transactions: TransactionService, seeded: dict[str, Transaction]
    ) -> None:
        assert _search(transactions, search="100%") == _ids(seeded, "rent")
        assert _search(transactions, search="k_b") == _ids(seeded, "snack")
        assert _search(transactions, search="%") == _ids(seeded, "rent")

    def test_amount(self, transactions: TransactionService, seeded: dict[str, Transaction]) -> None:
        assert _search(transactions, search="4 500") == _ids(seeded, "rent")
        assert _search(transactions, search="312,40") == _ids(seeded, "groceries")

    def test_whitespace_only_matches_everything(
        self, transactions: TransactionService, seeded: dict[str, Transaction]
    ) -> None:
        assert len(_search(transactions, search="   ")) == 5


class TestFilters:
    def test_types(self, transactions: TransactionService, seeded: dict[str, Transaction]) -> None:
        adjustments = frozenset(t for t in TransactionType if t.is_adjustment)
        assert _search(transactions, types=adjustments) == _ids(seeded, "fix")
        assert _search(transactions, types=frozenset({TransactionType.INCOME})) == _ids(
            seeded, "salary"
        )

    def test_date_range_is_inclusive(
        self, transactions: TransactionService, seeded: dict[str, Transaction]
    ) -> None:
        found = _search(transactions, start=date(2026, 5, 2), end=date(2026, 5, 20))
        assert found == _ids(seeded, "groceries", "rent")

    def test_category(
        self, transactions: TransactionService, seeded: dict[str, Transaction], food: Category
    ) -> None:
        assert _search(transactions, category_id=food.id) == _ids(seeded, "snack", "groceries")

    def test_combined(
        self, transactions: TransactionService, seeded: dict[str, Transaction], food: Category
    ) -> None:
        found = _search(transactions, category_id=food.id, start=date(2026, 6, 1), search="snack")
        assert found == _ids(seeded, "snack")


class TestTotals:
    def test_totals_cover_all_matches_not_just_the_page(
        self, transactions: TransactionService, seeded: dict[str, Transaction]
    ) -> None:
        page = transactions.search(TransactionQuery(limit=1))

        assert len(page.items) == 1
        assert page.total_count == 5
        assert page.income == Money.of("12000")
        assert page.expenses == Money.of("4824.80")  # adjustments are not expenses

    def test_totals_follow_filters(
        self, transactions: TransactionService, seeded: dict[str, Transaction]
    ) -> None:
        page = transactions.search(
            TransactionQuery(filters=TransactionFilter(start=date(2026, 5, 15)))
        )
        assert page.income == Money.zero()
        assert page.expenses == Money.of("324.80")

    def test_empty(self, transactions: TransactionService) -> None:
        page = transactions.search(TransactionQuery())
        assert (page.items, page.total_count, page.first_index, page.last_index) == ((), 0, 0, 0)
        assert page.income == Money.zero() and page.expenses == Money.zero()


class TestSorting:
    @pytest.mark.parametrize(
        ("sort", "descending", "expected"),
        [
            (TransactionSort.DATE, True, ["fix", "snack", "groceries", "rent", "salary"]),
            (TransactionSort.DATE, False, ["salary", "rent", "groceries", "snack", "fix"]),
            (TransactionSort.AMOUNT, True, ["salary", "fix", "snack", "groceries", "rent"]),
            (TransactionSort.AMOUNT, False, ["rent", "groceries", "snack", "fix", "salary"]),
            (TransactionSort.DESCRIPTION, False,
             ["rent", "fix", "groceries", "salary", "snack"]),
            (TransactionSort.TYPE, False, ["fix", "rent", "groceries", "snack", "salary"]),
        ],
    )
    def test_sort(
        self, transactions: TransactionService, seeded: dict[str, Transaction],
        sort: TransactionSort, descending: bool, expected: list[str],
    ) -> None:
        page = transactions.search(TransactionQuery(sort=sort, descending=descending))
        assert [t.id for t in page.items] == _ids(seeded, *expected)

    def test_sort_by_category_puts_uncategorised_first(
        self, transactions: TransactionService, seeded: dict[str, Transaction]
    ) -> None:
        page = transactions.search(TransactionQuery(sort=TransactionSort.CATEGORY, descending=False))
        names = [t.id for t in page.items]
        assert names[0] == seeded["fix"].id
        assert names[-1] == seeded["salary"].id  # Food < Rent < Salary


class TestPaging:
    def test_pages_are_stable_and_complete(
        self, transactions: TransactionService, add: AddTransaction, food: Category
    ) -> None:
        created = [add(TransactionType.EXPENSE, "10", food, on=date(2026, 6, 1)).id for _ in range(7)]
        query = TransactionQuery(limit=3)

        pages = [transactions.search(replace(query, offset=offset)) for offset in (0, 3, 6)]

        seen = [t.id for page in pages for t in page.items]
        assert sorted(seen) == sorted(created)  # no duplicates, nothing missing
        assert [p.has_previous for p in pages] == [False, True, True]
        assert [p.has_next for p in pages] == [True, True, False]
        assert (pages[2].first_index, pages[2].last_index, pages[2].total_count) == (7, 7, 7)

    @pytest.mark.parametrize(
        ("overrides", "field"),
        [
            ({"limit": 0}, "limit"),
            ({"limit": 501}, "limit"),
            ({"offset": -1}, "offset"),
            ({"filters": TransactionFilter(start=date(2026, 6, 2), end=date(2026, 6, 1))}, "start"),
            ({"filters": TransactionFilter(search="x" * 101)}, "search"),
        ],
    )
    def test_invalid_queries(
        self, transactions: TransactionService, overrides: dict[str, object], field: str
    ) -> None:
        with pytest.raises(ValidationError) as info:
            transactions.search(replace(TransactionQuery(), **overrides))  # type: ignore[arg-type]
        assert info.value.field == field
