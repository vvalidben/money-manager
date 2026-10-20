"""The opt-in update check (no network: the fetch is replaced)."""

import json
from datetime import date

import pytest

from money_manager.services import AppServices
from money_manager.services.update_service import (
    RELEASES_PAGE,
    UpdateCheckError,
    UpdateService,
    version_key,
)


def release(tag: str, url: str = "https://github.com/vvalidben/money-manager/releases/tag/x"):
    return lambda _url: json.dumps({"tag_name": tag, "html_url": url}).encode()


def test_off_by_default_and_daily(app_services: AppServices) -> None:
    updates = app_services.updates
    assert not updates.enabled() and not updates.due()
    updates.set_enabled(True)
    assert updates.due()
    service = UpdateService(app_services.settings, fetch=release("v9.0.0"),
                            today=lambda: date(2026, 6, 15))
    assert service.check().is_newer
    assert not service.due()  # checked today already


def test_versions(app_services: AppServices) -> None:
    newer = UpdateService(app_services.settings, fetch=release("v1.10.0"), current="1.9.3")
    assert newer.check().is_newer and newer.check().latest == "1.10.0"
    same = UpdateService(app_services.settings, fetch=release("1.4.0"), current="1.4.0")
    assert not same.check().is_newer
    assert version_key("v2.0") > version_key("1.99.99")


def test_only_links_to_this_project(app_services: AppServices) -> None:
    service = UpdateService(app_services.settings, fetch=release("v9", "https://evil.example/x"))
    assert service.check().url == RELEASES_PAGE


@pytest.mark.parametrize("answer", [b"not json", b"{}", b'{"tag_name": "latest"}'])
def test_unexpected_answers(app_services: AppServices, answer: bytes) -> None:
    service = UpdateService(app_services.settings, fetch=lambda _u: answer)
    with pytest.raises(UpdateCheckError):
        service.check()
