from PySide6.QtWidgets import QWidget

from money_manager.ui.components import EmptyState
from money_manager.ui.pages.base_page import BasePage
from money_manager.ui.pages.registry import PageSpec


class PlaceholderPage(BasePage):
    """Page for a section that is not implemented yet."""

    def __init__(self, spec: PageSpec, parent: QWidget | None = None) -> None:
        super().__init__(spec, parent)
        self.add_content(EmptyState(spec.placeholder_heading, spec.placeholder_message))
