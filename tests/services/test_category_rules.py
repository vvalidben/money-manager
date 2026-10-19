"""Category rules: learning, matching, managing, and using them on import."""

from datetime import timedelta
from pathlib import Path

import pytest

from money_manager.core.errors import NotFoundError, ValidationError
from money_manager.domain.categorize import CategoryRule, learn_keyword, match, normalize
from money_manager.domain.entities import Account, Category
from money_manager.domain.enums import CategoryKind
from money_manager.domain.statement import guess_columns
from money_manager.services import AppServices
from tests.services.support import fixed_today


class TestRules:
    @pytest.mark.parametrize(("description", "keyword"), [
        ("CB MARJANE CASA 18/10", "marjane"), ("VIREMENT SALAIRE ATLAS", "salaire"),
        ("PRLV INWI FIBRE", "inwi"), ("Café Bennis", "cafe"), ("Netflix.com", "netflix"),
        ("DAB 12/10 RETRAIT", None), ("", None),
    ])
    def test_learned_keyword(self, description: str, keyword: str | None) -> None:
        assert learn_keyword(description) == keyword

    def test_whole_words_and_most_specific_wins(self) -> None:
        rules = [CategoryRule(1, "marjane", 5, CategoryKind.EXPENSE),
                 CategoryRule(2, "marjane market", 6, CategoryKind.EXPENSE),
                 CategoryRule(3, "marjane", 7, CategoryKind.INCOME)]
        assert match("CB MARJANE MARKET", CategoryKind.EXPENSE, rules).id == 2  # type: ignore[union-attr]
        assert match("cb marjane casa", CategoryKind.EXPENSE, rules).id == 1  # type: ignore[union-attr]
        assert match("Remboursement Marjane", CategoryKind.INCOME, rules).id == 3  # type: ignore[union-attr]
        assert match("CB MARJANEX", CategoryKind.EXPENSE, rules) is None

    def test_normalize(self) -> None:
        assert normalize("  Électricité · LYDEC  ") == "electricite lydec"


@pytest.fixture
def groceries(app_services: AppServices) -> Category:
    return app_services.categories.create("Groceries", CategoryKind.EXPENSE)


class TestService:
    def test_learn_then_look_up(self, app_services: AppServices, groceries: Category) -> None:
        rule = app_services.category_rules.learn("CB MARJANE CASA 18/10", groceries.id)
        assert rule is not None and rule.keyword == "marjane"
        assert app_services.category_rules.category_for("CB MARJANE RABAT",
                                                        CategoryKind.EXPENSE) == groceries.id
        assert app_services.category_rules.category_for("CB MARJANE RABAT",
                                                        CategoryKind.INCOME) is None

    def test_learning_again_moves_the_rule(self, app_services: AppServices,
                                           groceries: Category) -> None:
        other = app_services.categories.create("Household", CategoryKind.EXPENSE)
        app_services.category_rules.learn("CB MARJANE", groceries.id)
        app_services.category_rules.learn("Marjane Rabat", other.id)
        [entry] = app_services.category_rules.entries()
        assert (entry.rule.keyword, entry.category_name) == ("marjane", "Household")

    def test_nothing_to_learn_from_noise(self, app_services: AppServices,
                                         groceries: Category) -> None:
        assert app_services.category_rules.learn("DAB 12/10", groceries.id) is None
        assert app_services.category_rules.entries() == []

    def test_add_and_remove_by_hand(self, app_services: AppServices,
                                    groceries: Category) -> None:
        rule = app_services.category_rules.add("  Carrefour Market ", groceries.id)
        assert rule.keyword == "carrefour market"
        with pytest.raises(ValidationError):
            app_services.category_rules.add("x", groceries.id)
        app_services.category_rules.remove(rule.id)
        with pytest.raises(NotFoundError):
            app_services.category_rules.remove(rule.id)

    def test_rules_go_with_their_category(self, app_services: AppServices,
                                          groceries: Category) -> None:
        app_services.category_rules.learn("CB MARJANE", groceries.id)
        app_services.categories.delete(groceries.id)
        assert app_services.category_rules.entries() == []


def test_import_uses_rules(app_services: AppServices, groceries: Category,
                           tmp_path: Path) -> None:
    bank: Account = app_services.accounts.create(
        "Bank", opening_balance="1000", opening_date=fixed_today() - timedelta(days=30))
    other = app_services.categories.create("Other spending", CategoryKind.EXPENSE)
    salary = app_services.categories.create("Salary", CategoryKind.INCOME)
    app_services.category_rules.learn("CB MARJANE", groceries.id)
    day = fixed_today().strftime("%d/%m/%Y")
    path = tmp_path / "s.csv"
    path.write_text(f"Date;Libellé;Montant\n{day};CB MARJANE RABAT;-100\n"
                    f"{day};CB AFRIQUIA;-50\n", encoding="utf-8")
    table = app_services.statements.read(path)
    preview = app_services.statements.preview(table, bank.id, guess_columns(table.header),
                                              "%d/%m/%Y")
    assert [p.category_id for p in preview.lines] == [groceries.id, None]
    assert preview.matched_count == 1
    app_services.statements.import_lines(bank.id, preview.new_lines,
                                         expense_category_id=other.id,
                                         income_category_id=salary.id)
    by_description = {t.description: t.category_id for t in app_services.transactions.list()}
    assert by_description == {"CB MARJANE RABAT": groceries.id, "CB AFRIQUIA": other.id}
