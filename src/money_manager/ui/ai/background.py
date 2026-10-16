"""Run a slow call (an AI request, a large calculation) off the UI thread.

The result or exception is delivered back on the UI thread through queued
signals, so callbacks may touch widgets and services freely. The callable
itself must not touch widgets. When an ``owner`` widget is given and has
been deleted by the time the result arrives (e.g. the window was rebuilt),
the callbacks are skipped.
"""

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from shiboken6 import isValid


class BackgroundCall(QObject):
    succeeded = Signal(object)
    failed = Signal(object)

    def __init__(self, work: Callable[[], Any], on_success: Callable[[Any], None],
                 on_failure: Callable[[BaseException], None],
                 owner: QObject | None = None) -> None:
        super().__init__()
        self.running = True
        self._work = work
        self._owner = owner
        queued = Qt.ConnectionType.QueuedConnection
        # Slots run in connection order: mark the call finished before the callbacks,
        # so they already see ``running`` as False (e.g. to re-enable buttons).
        self.succeeded.connect(self._finish, queued)
        self.failed.connect(self._finish, queued)
        self.succeeded.connect(lambda result: self._deliver(on_success, result), queued)
        self.failed.connect(lambda error: self._deliver(on_failure, error), queued)

    def _finish(self, _result: object) -> None:
        self.running = False

    def _deliver(self, callback: Callable[[Any], None], value: Any) -> None:
        if self._owner is None or isValid(self._owner):
            callback(value)

    def start(self, pool: QThreadPool | None = None) -> "BackgroundCall":
        (pool or QThreadPool.globalInstance()).start(_Runner(self))
        return self


class _Runner(QRunnable):
    def __init__(self, call: BackgroundCall) -> None:
        super().__init__()
        self._call = call

    def run(self) -> None:
        try:
            result = self._call._work()
        except BaseException as exc:  # delivered to the UI thread, which decides what to show
            self._call.failed.emit(exc)
        else:
            self._call.succeeded.emit(result)


def run_in_background(work: Callable[[], Any], on_success: Callable[[Any], None],
                      on_failure: Callable[[BaseException], None],
                      owner: QObject | None = None) -> BackgroundCall:
    """Keep a reference to the returned object until it has finished."""
    return BackgroundCall(work, on_success, on_failure, owner).start()
