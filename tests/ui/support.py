"""Helpers for UI tests with background work."""

import time
from collections.abc import Callable

from PySide6.QtWidgets import QApplication


def wait_until(condition: Callable[[], bool], timeout: float = 10.0) -> None:
    """Process Qt events until ``condition`` holds (background results arrive as events)."""
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError("timed out waiting for background work")
        QApplication.processEvents()
        time.sleep(0.005)
    QApplication.processEvents()
