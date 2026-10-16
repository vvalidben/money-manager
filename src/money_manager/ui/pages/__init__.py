"""Top-level pages shown in the main content area."""

from money_manager.ui.pages.base_page import BasePage
from money_manager.ui.pages.placeholder_page import PlaceholderPage
from money_manager.ui.pages.registry import (
    AI_ADVISOR_PAGE_KEY,
    DASHBOARD_PAGE_KEY,
    DEFAULT_PAGE_KEY,
    GOALS_PAGE_KEY,
    INVESTMENTS_PAGE_KEY,
    PAGES,
    SETTINGS_PAGE_KEY,
    STATISTICS_PAGE_KEY,
    SUBSCRIPTIONS_PAGE_KEY,
    TRANSACTIONS_PAGE_KEY,
    PageSpec,
)
from money_manager.ui.pages.settings_page import SettingsPage

__all__ = [
    "AI_ADVISOR_PAGE_KEY",
    "DASHBOARD_PAGE_KEY",
    "DEFAULT_PAGE_KEY",
    "GOALS_PAGE_KEY",
    "INVESTMENTS_PAGE_KEY",
    "PAGES",
    "SETTINGS_PAGE_KEY",
    "STATISTICS_PAGE_KEY",
    "SUBSCRIPTIONS_PAGE_KEY",
    "TRANSACTIONS_PAGE_KEY",
    "BasePage",
    "PageSpec",
    "PlaceholderPage",
    "SettingsPage",
]
