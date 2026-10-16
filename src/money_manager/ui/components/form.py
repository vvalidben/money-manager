from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from money_manager.ui.theme import Spacing, set_style_property


class FormField(QWidget):
    """A labelled input with an inline error message underneath.

    ``highlight`` is the widget outlined on error when ``widget`` is a
    container (e.g. an edit plus a currency label); it defaults to ``widget``.
    """

    def __init__(
        self,
        label: str,
        widget: QWidget,
        parent: QWidget | None = None,
        *,
        highlight: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.widget = highlight or widget

        self.label = QLabel(label)
        self.label.setObjectName("FieldLabel")
        self.label.setBuddy(self.widget)

        self.error_label = QLabel()
        self.error_label.setObjectName("FieldError")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.XS)
        layout.addWidget(self.label)
        layout.addWidget(widget)
        layout.addWidget(self.error_label)

    @property
    def error(self) -> str:
        return self.error_label.text() if not self.error_label.isHidden() else ""

    def set_error(self, message: str | None) -> None:
        self.error_label.setText(message or "")
        self.error_label.setVisible(bool(message))
        set_style_property(self.widget, "invalid", bool(message))
