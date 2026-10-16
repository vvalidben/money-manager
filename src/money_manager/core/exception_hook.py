"""Last-resort handler for exceptions nobody caught.

PySide6 routes exceptions raised inside Qt slots to ``sys.excepthook``, so this
hook also covers errors triggered from the UI. The UI layer supplies the
``notify`` callback; this module stays free of Qt.
"""

import logging
import sys
from collections.abc import Callable
from types import TracebackType

logger = logging.getLogger(__name__)

ErrorNotifier = Callable[[BaseException], None]


def install_exception_hook(notify: ErrorNotifier | None = None) -> None:
    """Log every uncaught exception and optionally tell the user about it."""

    def handle(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
        if notify is None:
            return
        try:
            notify(exc_value)
        except Exception:
            logger.exception("Failed to notify the user about an unhandled exception")

    sys.excepthook = handle
