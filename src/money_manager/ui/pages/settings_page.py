"""Settings: storage, currency, AI, export/import, privacy, reset and app information.

Changing the currency, importing a backup or resetting replaces data the
services and pages were built with, so the page asks the main window to
rebuild everything (``reload_requested``).
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from money_manager.core.config import AppConfig
from money_manager.services import AppServices
from money_manager.ui.ai.settings_card import AISettingsCard
from money_manager.ui.pages.base_page import BasePage
from money_manager.ui.pages.registry import SETTINGS_PAGE_KEY, PageSpec
from money_manager.ui.settings.cards import (
    AboutCard,
    CurrencyCard,
    DataCard,
    PrivacyCard,
    ResetCard,
    StorageCard,
)
from money_manager.ui.theme import Spacing


class SettingsPage(BasePage):
    reload_requested = Signal(str)  # page to show after the rebuild

    def __init__(self, spec: PageSpec, config: AppConfig, services: AppServices,
                 parent: QWidget | None = None) -> None:
        super().__init__(spec, parent, fill=True)
        self.storage_card = StorageCard(config)
        self.currency_card = CurrencyCard(services)
        self.ai_card = AISettingsCard(services)
        self.data_card = DataCard(services)
        self.privacy_card = PrivacyCard()
        self.reset_card = ResetCard(services)
        self.about_card = AboutCard(services, config)
        for card in (self.currency_card, self.data_card, self.reset_card):
            card.changed.connect(lambda: self.reload_requested.emit(SETTINGS_PAGE_KEY))

        content = QWidget()
        content.setObjectName("TransparentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, Spacing.SM, 0)
        content_layout.setSpacing(Spacing.MD)
        for card in (self.storage_card, self.currency_card, self.ai_card, self.data_card,
                     self.privacy_card, self.reset_card, self.about_card):
            content_layout.addWidget(card)
        content_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        self.add_content(scroll, stretch=1)

    def on_shown(self) -> None:
        self.currency_card.load()
        self.ai_card.load()
