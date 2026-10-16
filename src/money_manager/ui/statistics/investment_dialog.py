"""Choose which expense categories count as investing (saving, not spending)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError
from money_manager.domain.enums import CategoryKind
from money_manager.services import AppServices
from money_manager.ui.theme import Spacing


class InvestmentCategoriesDialog(QDialog):
    def __init__(self, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._services = services
        self.setWindowTitle("Investment categories")
        self.setModal(True)
        self.setMinimumWidth(420)

        intro = QLabel(
            "Tick the expense categories where money goes into investments (stocks, "
            "retirement funds, …). They count towards your investment rate and as "
            "saving rather than spending."
        )
        intro.setObjectName("CardBody")
        intro.setWordWrap(True)

        self.list = QListWidget()
        self._original: dict[int, bool] = {}
        categories = services.categories.list(CategoryKind.EXPENSE, include_archived=True)
        for category in sorted(categories, key=lambda c: c.name.casefold()):
            label = category.name + (" (archived)" if category.is_archived else "")
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, category.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if category.is_investment else Qt.CheckState.Unchecked
            )
            self.list.addItem(item)
            self._original[category.id] = category.is_investment

        self.empty_label = QLabel("No expense categories yet.")
        self.empty_label.setObjectName("MutedLabel")
        self.empty_label.setVisible(not categories)

        self.form_error = QLabel()
        self.form_error.setObjectName("FormError")
        self.form_error.setWordWrap(True)
        self.form_error.hide()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("PrimaryButton")
        buttons.accepted.connect(self.submit)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        layout.addWidget(intro)
        layout.addWidget(self.form_error)
        layout.addWidget(self.list)
        layout.addWidget(self.empty_label)
        layout.addWidget(buttons)

    def set_checked(self, category_id: int, checked: bool) -> None:
        for index in range(self.list.count()):
            item = self.list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == category_id:
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)

    def submit(self) -> bool:
        try:
            for index in range(self.list.count()):
                item = self.list.item(index)
                category_id = item.data(Qt.ItemDataRole.UserRole)
                checked = item.checkState() == Qt.CheckState.Checked
                if checked != self._original[category_id]:
                    self._services.categories.set_investment(category_id, checked)
        except MoneyManagerError as exc:
            self.form_error.setText(str(exc))
            self.form_error.show()
            return False
        self.accept()
        return True
