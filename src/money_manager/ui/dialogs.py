"""User-facing message and confirmation dialogs.

Pages call these module functions (rather than QMessageBox directly) so tests
can replace them without opening modal windows.
"""

from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget

from money_manager.core.errors import MoneyManagerError

UNEXPECTED_ERROR_MESSAGE = (
    "An unexpected error occurred. Your data has not been sent anywhere; "
    "technical details were written to the log file."
)


def show_error(parent: QWidget | None, title: str, message: str) -> None:
    QMessageBox.critical(parent, title, message)


def show_warning(parent: QWidget | None, title: str, message: str) -> None:
    QMessageBox.warning(parent, title, message)


def show_info(parent: QWidget | None, title: str, message: str) -> None:
    QMessageBox.information(parent, title, message)


def ask_save_path(parent: QWidget | None, title: str, suggested: Path,
                  file_filter: str) -> Path | None:
    """Ask where to save a file; None when cancelled."""
    chosen, _ = QFileDialog.getSaveFileName(parent, title, str(suggested), file_filter)
    return Path(chosen) if chosen else None


def ask_open_path(parent: QWidget | None, title: str, start: Path,
                  file_filter: str) -> Path | None:
    """Ask for an existing file; None when cancelled."""
    chosen, _ = QFileDialog.getOpenFileName(parent, title, str(start), file_filter)
    return Path(chosen) if chosen else None


def choose(
    parent: QWidget | None, title: str, message: str, options: list[tuple[str, str]]
) -> str | None:
    """Ask the user to pick one of ``options`` ((key, button text) pairs); None = cancelled."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setText(message)
    buttons = {
        box.addButton(text, QMessageBox.ButtonRole.AcceptRole): key for key, text in options
    }
    cancel = box.addButton(QMessageBox.StandardButton.Cancel)
    box.setDefaultButton(cancel)
    box.exec()
    return buttons.get(box.clickedButton())


def confirm_destructive(
    parent: QWidget | None, title: str, message: str, confirm_text: str = "Delete"
) -> bool:
    """Ask before an irreversible action. Cancel is the default button."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(title)
    box.setText(message)
    confirm = box.addButton(confirm_text, QMessageBox.ButtonRole.DestructiveRole)
    cancel = box.addButton(QMessageBox.StandardButton.Cancel)
    box.setDefaultButton(cancel)
    box.exec()
    return box.clickedButton() is confirm


def show_unexpected_error(exc: BaseException) -> None:
    """Notifier for the global exception hook."""
    if QApplication.instance() is None:
        return
    message = str(exc) if isinstance(exc, MoneyManagerError) else UNEXPECTED_ERROR_MESSAGE
    show_error(QApplication.activeWindow(), "Something went wrong", message)
