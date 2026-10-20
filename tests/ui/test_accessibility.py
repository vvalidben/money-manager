"""Every control a keyboard or screen-reader user meets has a name."""

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QLineEdit,
    QWidget,
)

from money_manager.core.config import AppConfig
from money_manager.domain.entities import TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.services import AppServices
from money_manager.ui.main_window import MainWindow
from money_manager.ui.pages import PAGES


def _named(widget: QWidget) -> bool:
    text = widget.text().strip() if isinstance(widget, (QAbstractButton,)) else ""
    placeholder = widget.placeholderText() if isinstance(widget, QLineEdit) else ""
    return bool(text or widget.accessibleName() or widget.toolTip() or placeholder)


def unnamed_controls(window: MainWindow) -> list[str]:
    problems = []
    for spec in PAGES:
        window.show_page(spec.key)
        QApplication.processEvents()
        page = window.current_page
        controls = (page.findChildren(QAbstractButton) + page.findChildren(QLineEdit)
                    + page.findChildren(QComboBox) + page.findChildren(QAbstractSpinBox))
        for control in controls:
            if not control.isVisibleTo(page) or _named(control):
                continue
            if isinstance(control, QAbstractButton) and isinstance(control.parent(), QLineEdit) \
                    and control.focusPolicy() == Qt.FocusPolicy.NoFocus:
                continue  # an icon inside a field, not reachable by keyboard
            if isinstance(control, QLineEdit) and isinstance(control.parent(),
                                                             (QComboBox, QAbstractSpinBox)):
                continue  # the editor inside a combo or spin box (the box has the name)
            problems.append(f"{spec.key}: {type(control).__name__} "
                            f"{control.objectName() or '(no object name)'}")
    return problems


def test_every_control_has_a_name(qapp: QApplication, app_config: AppConfig,
                                  app_services: AppServices) -> None:
    bank = app_services.accounts.create("Bank", opening_balance="100",
                                        opening_date=date(2026, 1, 1))
    food = app_services.categories.create("Food", CategoryKind.EXPENSE)
    app_services.transactions.create(TransactionDraft(bank.id, TransactionType.EXPENSE, "5",
                                                      date(2026, 6, 1), food.id))
    window = MainWindow(app_config, app_services)
    window.resize(1280, 860)
    window.show()
    try:
        assert unnamed_controls(window) == []
    finally:
        window.close()
