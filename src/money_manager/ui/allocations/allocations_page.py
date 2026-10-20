"""Money / Allocations page: what is set aside for what, and what is Available."""

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QInputDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError
from money_manager.domain.allocation import AllocationSummary
from money_manager.domain.entities import Allocation
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.allocations.dialogs import AllocationDialog, MoveMoneyDialog
from money_manager.ui.allocations.view_model import (
    AllocationCardView,
    MoveView,
    allocation_cards,
    move_views,
    over_allocation_note,
    summary_stats,
)
from money_manager.ui.components import Card, EmptyState, FlowRow, ResponsiveRow, StatCard
from money_manager.ui.pages.base_page import BasePage
from money_manager.ui.pages.registry import PageSpec
from money_manager.ui.theme import Spacing
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

BAR_STEPS = 1000
ALLOCATION_CARD_MIN_WIDTH = 320


class AllocationCard(Card):
    add_requested = Signal(int)
    take_requested = Signal(int)
    rename_requested = Signal(int)
    archive_requested = Signal(int)

    def __init__(self, view: AllocationCardView, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.view = view
        self.body.setSpacing(Spacing.SM)
        title = QLabel(view.name)
        title.setObjectName("CardHeading")
        title.setWordWrap(True)
        self.body.addWidget(title)
        balance = QLabel(view.balance)
        balance.setObjectName("StatValueCompact")
        self.body.addWidget(balance)
        self.bar = QProgressBar()
        self.bar.setObjectName("ShareBar")
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        self.bar.setRange(0, BAR_STEPS)
        self.bar.setValue(int(view.share_fraction * BAR_STEPS))  # drawing only
        self.body.addWidget(self.bar)
        for text in (view.share, view.goal):
            if text:
                label = QLabel(text)
                label.setObjectName("MutedLabel")
                label.setWordWrap(True)
                self.body.addWidget(label)

        add = QPushButton(tr("Add money"))
        add.setObjectName("PrimaryButton")
        add.clicked.connect(lambda: self.add_requested.emit(view.allocation_id))
        take = QPushButton(tr("Take out"))
        take.clicked.connect(lambda: self.take_requested.emit(view.allocation_id))
        rename = QPushButton(tr("Rename"))
        rename.clicked.connect(lambda: self.rename_requested.emit(view.allocation_id))
        self.archive_button = QPushButton(tr("Archive"))
        self.archive_button.setObjectName("DangerButton")
        self.archive_button.clicked.connect(lambda: self.archive_requested.emit(view.allocation_id))
        self.archive_button.setEnabled(view.can_archive)
        self.archive_button.setToolTip(
            tr("Returns its money to Available") if view.can_archive
            else tr("This allocation holds a goal's money; manage it on the Goals page"))
        self.body.addStretch(1)
        # Four buttons wrap onto a second line in narrow cards instead of being squeezed.
        self.body.addWidget(FlowRow([add, take, rename, self.archive_button]))


class AllocationsPage(BasePage):
    def __init__(self, spec: PageSpec, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(spec, parent, fill=True)
        self._services = services
        self.summary: AllocationSummary | None = None
        self.cards: list[AllocationCard] = []
        self.moves: tuple[MoveView, ...] = ()
        self.archived: list[Allocation] = []

        self.new_button = QPushButton(tr("New allocation"))
        self.new_button.setObjectName("PrimaryButton")
        self.new_button.setToolTip(tr("New allocation (Ctrl+N)"))
        self.new_button.clicked.connect(self.create_allocation)
        self.header.add_action(self.new_button)
        self.primary_button = self.new_button
        self.move_button = QPushButton(tr("Move money"))
        self.move_button.clicked.connect(lambda: self.move_money(None, None))
        self.header.add_action(self.move_button)

        self.stat_cards = tuple(StatCard("", compact=True) for _ in range(4))
        self.stats_row = ResponsiveRow(self.stat_cards, min_item_width=190)
        self.warning = QLabel()
        self.warning.setObjectName("CautionNotice")
        self.warning.setWordWrap(True)
        self.warning.hide()
        self.empty_state = EmptyState(
            tr("Nothing set aside yet"),
            tr("Allocations organise the money you already have: set some aside for bills, a "
            "holiday or an emergency fund. It stays in your accounts, but is no longer "
            "counted as Available to spend. Goals keep their money in allocations too."),
            badge=None,
            action_text=tr("Create an allocation"),
        )
        self.empty_state.action_clicked.connect(self.create_allocation)

        self.cards_host = QWidget()
        self.cards_host.setObjectName("TransparentArea")
        self.cards_layout = QVBoxLayout(self.cards_host)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)

        self.moves_card = Card(tr("Recent moves"))
        self.moves_grid = QGridLayout()
        self.moves_grid.setHorizontalSpacing(Spacing.MD)
        self.moves_grid.setVerticalSpacing(Spacing.XS)
        self.moves_card.body.addLayout(self.moves_grid)
        self.archived_card = Card(tr("Archived"))
        self.archived_grid = QGridLayout()
        self.archived_card.body.addLayout(self.archived_grid)

        content = QWidget()
        content.setObjectName("TransparentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, Spacing.SM, 0)
        content_layout.setSpacing(Spacing.MD)
        for widget in (self.stats_row, self.warning, self.empty_state, self.cards_host,
                       self.moves_card, self.archived_card):
            content_layout.addWidget(widget)
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
            summary = self._services.allocations.summary()
            everything = self._services.allocations.list(include_archived=True)
            goal_names = {g.goal.allocation_id: g.goal.name for g in self._services.goals.list()
                          if g.goal.allocation_id is not None}
            transfers = self._services.transfers.list()
        except MoneyManagerError as exc:
            logger.warning("Could not load allocations: %s", exc)
            dialogs.show_warning(self, tr("Could not load allocations"), str(exc))
            return
        self.summary = summary
        for card, stat in zip(self.stat_cards, summary_stats(summary), strict=True):
            card.label.setText(stat.label)
            card.set_value(stat.value, stat.tone)
            card.set_caption(stat.caption)
        note = over_allocation_note(summary)
        self.warning.setText(note)
        self.warning.setVisible(bool(note))
        views = allocation_cards(summary, goal_names)
        self._rebuild_cards(views)
        names = {a.id: a.name for a in everything}
        self.moves = move_views(transfers, names)
        self._rebuild_moves()
        self.archived = [a for a in everything if a.is_archived]
        self._rebuild_archived()
        has_any = bool(views)
        self.empty_state.setVisible(not has_any)
        for widget in (self.new_button, self.cards_host):
            widget.setVisible(has_any)
        self.moves_card.setVisible(bool(self.moves))
        self.archived_card.setVisible(bool(self.archived))

    def card_for(self, allocation_id: int) -> AllocationCard:
        return next(card for card in self.cards if card.view.allocation_id == allocation_id)

    # ------------------------------------------------------------ building

    def _rebuild_cards(self, views: tuple[AllocationCardView, ...]) -> None:
        _clear(self.cards_layout)
        self.cards = []
        for view in views:
            card = AllocationCard(view)
            card.add_requested.connect(lambda aid: self.move_money(None, aid))
            card.take_requested.connect(lambda aid: self.move_money(aid, None))
            card.rename_requested.connect(self.rename_allocation)
            card.archive_requested.connect(self.archive_allocation)
            self.cards.append(card)
        if self.cards:
            self.cards_layout.addWidget(ResponsiveRow(self.cards, ALLOCATION_CARD_MIN_WIDTH))

    def _rebuild_moves(self) -> None:
        _clear(self.moves_grid)
        for row, move in enumerate(self.moves):
            cells = (move.date, move.route, move.note)
            for column, text in enumerate(cells):
                label = QLabel(text)
                label.setObjectName("MutedLabel" if column != 1 else "FieldValue")
                self.moves_grid.addWidget(label, row, column)
            amount = QLabel(move.amount)
            amount.setObjectName("AllocationAmount")
            self.moves_grid.addWidget(amount, row, 3, Qt.AlignmentFlag.AlignRight)
            undo = QPushButton(tr("Undo"))
            undo.setToolTip(tr("Return this money to where it came from"))
            undo.clicked.connect(lambda _c=False, tid=move.transfer_id: self.undo_move(tid))
            self.moves_grid.addWidget(undo, row, 4)
        self.moves_grid.setColumnStretch(2, 1)

    def _rebuild_archived(self) -> None:
        _clear(self.archived_grid)
        for row, allocation in enumerate(self.archived):
            self.archived_grid.addWidget(QLabel(allocation.name), row, 0)
            restore = QPushButton(tr("Restore"))
            restore.clicked.connect(lambda _c=False, aid=allocation.id: self.restore(aid))
            self.archived_grid.addWidget(restore, row, 1, Qt.AlignmentFlag.AlignRight)
        self.archived_grid.setColumnStretch(0, 1)

    # ------------------------------------------------------------ actions

    def create_allocation(self) -> None:
        dialog = self.make_allocation_dialog()
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved is not None:
            self.refresh()
            self.notice.emit(tr("Allocation created"), dialog.saved.name)

    def move_money(self, from_id: int | None, to_id: int | None) -> None:
        dialog = self.make_move_dialog(from_id, to_id)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved is not None:
            self.refresh()
            [move] = move_views([dialog.saved], {a.id: a.name for a in
                                                 self._services.allocations.list()})
            self.notice.emit(tr("Money moved"), f"{move.amount} · {move.route}")

    def rename_allocation(self, allocation_id: int) -> None:
        current = self.card_for(allocation_id).view.name
        name, accepted = QInputDialog.getText(self, tr("Rename allocation"), tr("New name:"),
                                              text=current)
        if not accepted or not name.strip() or name.strip() == current:
            return
        try:
            renamed = self._services.allocations.rename(allocation_id, name)
        except MoneyManagerError as exc:
            dialogs.show_warning(self, tr("Could not rename the allocation"), str(exc))
            return
        self.refresh()
        self.notice.emit(tr("Allocation renamed"), renamed.name)

    def archive_allocation(self, allocation_id: int) -> None:
        view = self.card_for(allocation_id).view
        message = (tr("Archive {0}?\n\nIts {1} goes back to Available. You can restore the "
                      "allocation later from the Archived list.", view.name, view.balance))
        if not dialogs.confirm_destructive(self, tr("Archive allocation"), message, tr("Archive")):
            return
        try:
            self._services.allocations.archive(allocation_id)
        except MoneyManagerError as exc:
            dialogs.show_warning(self, tr("Could not archive the allocation"), str(exc))
            return
        self.refresh()
        self.notice.emit(tr("Allocation archived"), tr("{0} · {1} to Available", view.name, view.balance))

    def undo_move(self, transfer_id: int) -> None:
        move = next(m for m in self.moves if m.transfer_id == transfer_id)
        if not dialogs.confirm_destructive(self, tr("Undo move"),
                                           tr("Undo this move?\n\n{0} · {1} · {2}", move.date, move.route, move.amount), tr("Undo")):
            return
        try:
            self._services.transfers.undo(transfer_id)
        except MoneyManagerError as exc:
            dialogs.show_warning(self, tr("Could not undo the move"), str(exc))
            return
        self.refresh()
        self.notice.emit(tr("Move undone"), f"{move.amount} · {move.route}")

    def restore(self, allocation_id: int) -> None:
        try:
            allocation = self._services.allocations.restore(allocation_id)
        except MoneyManagerError as exc:
            dialogs.show_warning(self, tr("Could not restore the allocation"), str(exc))
            return
        self.refresh()
        self.notice.emit(tr("Allocation restored"), allocation.name)

    # Separate so tests can substitute non-modal fakes.
    def make_allocation_dialog(self) -> AllocationDialog:
        return AllocationDialog(self._services, parent=self)

    def make_move_dialog(self, from_id: int | None, to_id: int | None) -> MoveMoneyDialog:
        return MoveMoneyDialog(self._services, from_id=from_id, to_id=to_id, parent=self)


def _clear(layout: QVBoxLayout | QGridLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget() if item is not None else None
        if widget is not None:
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()

