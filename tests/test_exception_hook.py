import logging
import sys

import pytest

from money_manager.core.exception_hook import install_exception_hook


def _raise_and_capture(exc: BaseException) -> tuple[type[BaseException], BaseException, object]:
    try:
        raise exc
    except BaseException:
        info = sys.exc_info()
    assert info[0] is not None and info[1] is not None
    return info[0], info[1], info[2]


@pytest.fixture(autouse=True)
def _restore_excepthook(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)


def test_logs_and_notifies(caplog: pytest.LogCaptureFixture) -> None:
    notified: list[BaseException] = []
    install_exception_hook(notify=notified.append)
    error = RuntimeError("boom")

    with caplog.at_level(logging.CRITICAL):
        sys.excepthook(*_raise_and_capture(error))

    assert notified == [error]
    assert "Unhandled exception" in caplog.text
    assert "boom" in caplog.text


def test_failing_notifier_does_not_raise(caplog: pytest.LogCaptureFixture) -> None:
    def broken_notifier(_exc: BaseException) -> None:
        raise ValueError("dialog failed")

    install_exception_hook(notify=broken_notifier)

    sys.excepthook(*_raise_and_capture(RuntimeError("boom")))

    assert "Failed to notify" in caplog.text


def test_works_without_notifier(caplog: pytest.LogCaptureFixture) -> None:
    install_exception_hook()

    sys.excepthook(*_raise_and_capture(RuntimeError("boom")))

    assert "Unhandled exception" in caplog.text
