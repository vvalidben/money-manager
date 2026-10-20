"""Accounts page: every account with its balance, and ways to manage them."""

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError
from money_manager.domain.balance import BalanceBreakdown
from money_manager.domain.entities import Account
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.accounts.account_dialog import AccountDialog
from money_manager.ui.accounts.correct_balance_dialog import CorrectBalanceDialog
from money_manager.ui.accounts.view_model import AccountCardView, account_cards, summary_stats
from money_manager.ui.components import Card, EmptyState, ResponsiveRow, StatCard
from money_manager.ui.debts.loans_card import LoansCard
from money_manager.ui.formatting import format_money, format_signed_money
from money_manager.ui.pages.base_page import BasePage
from money_manager.ui.pages.registry import PageSpec
from money_manager.ui.theme import Spacing, set_style_property
from money_manager.ui.transactions.transfer_dialog import TransferDialog
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

BAR_STEPS = 1000
ACCOUNT_CARD_MIN_WIDTH = 320


class AccountCard(Card):
    correct_requested = Signal(int)
    edit_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(self, view: AccountCardView, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.view = view
        self.body.setSpacing(Spacing.SM)

        title = QLabel(view.name)
        title.setObjectName("CardHeading")
        title.setWordWrap(True)
        self.body.addWidget(title)
        self.balance_label = QLabel(view.balance)
        self.balance_label.setObjectName("StatValueCompact")
        set_style_property(self.balance_label, "tone", "outflow" if view.is_negative else "neutral")
        self.body.addWidget(self.balance_label)

        self.bar = QProgressBar()
        self.bar.setObjectName("ShareBar")
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        self.bar.setRange(0, BAR_STEPS)
        self.bar.setValue(int(view.share_fraction * BAR_STEPS))  # drawing only
        self.body.addWidget(self.bar)
        for text in (view.share, view.since, view.activity):
            label = QLabel(text)
            label.setObjectName("MutedLabel")
            label.setWordWrap(True)
            self.body.addWidget(label)

        actions = QHBoxLayout()
        actions.setSpacing(Spacing.SM)
        correct = QPushButton(tr("Correct balance…"))
        correct.setToolTip(tr("Match the balance your bank shows (recorded as an adjustment)"))
        correct.clicked.connect(lambda: self.correct_requested.emit(view.account_id))
        edit = QPushButton(tr("Edit"))
        edit.clicked.connect(lambda: self.edit_requested.emit(view.account_id))
        delete = QPushButton(tr("Delete"))
        delete.setObjectName("DangerButton")
        delete.clicked.connect(lambda: self.delete_requested.emit(view.account_id))
        actions.addWidget(correct)
        actions.addStretch(1)
        actions.addWidget(edit)
        actions.addWidget(delete)
        self.body.addStretch(1)
        self.body.addLayout(actions)


class AccountsPage(BasePage):
    def __init__(self, spec: PageSpec, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(spec, parent, fill=True)
        self._services = services
        self.accounts: list[Account] = []
        self.breakdowns: dict[int, BalanceBreakdown] = {}
        self.cards: list[AccountCard] = []

        self.new_button = QPushButton(tr("New account"))
        self.new_button.setObjectName("PrimaryButton")
        self.new_button.setToolTip(tr("New account (Ctrl+N)"))
        self.new_button.clicked.connect(self.create_account)
        self.header.add_action(self.new_button)
        self.primary_button = self.new_button
        self.transfer_button = QPushButton(tr("Transfer"))
        self.transfer_button.setToolTip(tr("Move money between two of your accounts"))
        self.transfer_button.clicked.connect(self.transfer)
        self.header.add_action(self.transfer_button)

        self.stat_cards = tuple(StatCard("", compact=True) for _ in range(4))
        self.stats_row = ResponsiveRow(self.stat_cards, min_item_width=190)
        self.empty_state = EmptyState(
            tr("No accounts yet"),
            tr("An account is where your money is kept: a bank account, your cash wallet or a "
            "card. Add the first one with the balance it has today."),
            badge=None,
            action_text=tr("Create account"),
        )
        self.empty_state.action_clicked.connect(self.create_account)

        self.cards_host = QWidget()
        self.cards_host.setObjectName("TransparentArea")
        self.cards_layout = QVBoxLayout(self.cards_host)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)

        content = QWidget()
        content.setObjectName("TransparentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, Spacing.SM, 0)
        content_layout.setSpacing(Spacing.MD)
        content_layout.addWidget(self.stats_row)
        content_layout.addWidget(self.empty_state)
        content_layout.addWidget(self.cards_host)
        self.loans_card = LoansCard(services)
        self.loans_card.changed.connect(self._loans_changed)
        content_layout.addWidget(self.loans_card)
        content_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        self.add_content(scroll, stretch=1)

    def on_shown(self) -> None:
        if self.already_current(self._services.freshness()):
            return
        self.refresh()

    def refresh(self) -> None:
        try:
            accounts = self._services.accounts.list()
            breakdowns = {a.id: self._services.balances.breakdown(a.id) for a in accounts}
        except MoneyManagerError as exc:
            logger.warning("Could not load accounts: %s", exc)
            dialogs.show_warning(self, tr("Could not load accounts"), str(exc))
            return
        self.accounts, self.breakdowns = accounts, breakdowns
        for card, stat in zip(self.stat_cards, summary_stats(breakdowns,
                                                             self._services.base_currency),
                              strict=True):
            card.label.setText(stat.label)
            card.set_value(stat.value, stat.tone)
            card.set_caption(stat.caption)
        self._rebuild_cards(account_cards(accounts, breakdowns))
        has_accounts = bool(accounts)
        self.empty_state.setVisible(not has_accounts)
        for widget in (self.new_button, self.stats_row, self.cards_host, self.loans_card):
            widget.setVisible(has_accounts)
        self.loans_card.load()
        self.transfer_button.setVisible(has_accounts)
        self.transfer_button.setEnabled(len(accounts) > 1)

    def _loans_changed(self, title: str, detail: str) -> None:
        self.refresh()  # balances move when a loan goes through an account
        self.notice.emit(title, detail)

    def card_for(self, account_id: int) -> AccountCard:
        return next(card for card in self.cards if card.view.account_id == account_id)

    def _account(self, account_id: int) -> Account:
        return next(account for account in self.accounts if account.id == account_id)

    def _rebuild_cards(self, views: tuple[AccountCardView, ...]) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self.cards = []
        for view in views:
            card = AccountCard(view)
            card.correct_requested.connect(self.correct_balance)
            card.edit_requested.connect(self.edit_account)
            card.delete_requested.connect(self.delete_account)
            self.cards.append(card)
        if self.cards:
            self.cards_layout.addWidget(ResponsiveRow(self.cards, ACCOUNT_CARD_MIN_WIDTH))

    # ------------------------------------------------------------ actions

    def create_account(self) -> None:
        dialog = self.make_account_dialog(None)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved is not None:
            self.refresh()
            self.notice.emit(tr("Account created"), dialog.saved.name)

    def edit_account(self, account_id: int) -> None:
        dialog = self.make_account_dialog(self._account(account_id))
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved is not None:
            self.refresh()
            self.notice.emit(tr("Account updated"), dialog.saved.name)

    def correct_balance(self, account_id: int) -> None:
        account = self._account(account_id)
        dialog = self.make_correct_dialog(account)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.refresh()
        if dialog.adjustment is None:
            self.notice.emit(tr("Balance already correct"), account.name)
        else:
            self.notice.emit(tr("Balance corrected"), tr("{0} · adjustment {1}", account.name, format_signed_money(dialog.adjustment.signed_amount)))

    def delete_account(self, account_id: int) -> None:
        account = self._account(account_id)
        message = (tr("Delete the account {0}?\n\nOnly an account without any transactions can "
                      "be deleted. This cannot be undone.", account.name))
        if not dialogs.confirm_destructive(self, tr("Delete account"), message):
            return
        try:
            self._services.accounts.delete(account_id)
        except MoneyManagerError as exc:
            dialogs.show_warning(self, tr("Could not delete the account"), str(exc))
            return
        self.refresh()
        self.notice.emit(tr("Account deleted"), account.name)

    def transfer(self) -> None:
        dialog = self.make_transfer_dialog()
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved is not None:
            transfer = dialog.saved
            self.refresh()
            names = {a.id: a.name for a in self.accounts}
            self.notice.emit(tr("Transfer recorded"),
                             f"{format_money(transfer.amount)} · "
                             f"{names.get(transfer.from_account_id, '?')} → "
                             f"{names.get(transfer.to_account_id, '?')}")

    # Separate so tests can substitute non-modal fakes.
    def make_account_dialog(self, account: Account | None) -> AccountDialog:
        return AccountDialog(self._services, parent=self, account=account)

    def make_correct_dialog(self, account: Account) -> CorrectBalanceDialog:
        return CorrectBalanceDialog(self._services, account,
                                    self.breakdowns[account.id].balance, parent=self)

    def make_transfer_dialog(self) -> TransferDialog:
        return TransferDialog(self._services, parent=self)
