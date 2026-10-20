"""Single source of truth for the application's pages and their order."""

from dataclasses import dataclass
from money_manager.core.i18n import tr


@dataclass(frozen=True, slots=True)
class PageSpec:
    key: str
    nav_label: str
    title: str
    subtitle: str
    placeholder_heading: str
    placeholder_message: str


DASHBOARD_PAGE_KEY = "dashboard"
ACCOUNTS_PAGE_KEY = "accounts"
DEFAULT_PAGE_KEY = DASHBOARD_PAGE_KEY
SETTINGS_PAGE_KEY = "settings"
TRANSACTIONS_PAGE_KEY = "transactions"
BUDGETS_PAGE_KEY = "budgets"
ALLOCATIONS_PAGE_KEY = "allocations"
STATISTICS_PAGE_KEY = "statistics"
GOALS_PAGE_KEY = "goals"
SUBSCRIPTIONS_PAGE_KEY = "subscriptions"
INVESTMENTS_PAGE_KEY = "investments"
AI_ADVISOR_PAGE_KEY = "ai_advisor"

# Sidebar order; Ctrl+1…9 follow it. Each page's colour lives in ui.theme.PAGE_FILLS.
PAGES: tuple[PageSpec, ...] = (
    PageSpec(
        key=DASHBOARD_PAGE_KEY,
        nav_label=tr("Dashboard"),
        title=tr("Dashboard"),
        subtitle=tr("Your financial overview at a glance."),
        placeholder_heading=tr("Your overview will live here"),
        placeholder_message=(
            tr("Once you start recording transactions, this page will summarise your balance, "
            "how your money is allocated and how this month compares to the last.")
        ),
    ),
    PageSpec(
        key=ACCOUNTS_PAGE_KEY,
        nav_label=tr("Accounts"),
        title=tr("Accounts"),
        subtitle=tr("Where your money is kept, and how much is in each account."),
        placeholder_heading=tr("No accounts yet"),
        placeholder_message=tr("Add the account you want to track first."),
    ),
    PageSpec(
        key=TRANSACTIONS_PAGE_KEY,
        nav_label=tr("Transactions"),
        title=tr("Transactions"),
        subtitle=tr("Money that actually enters or leaves your accounts."),
        placeholder_heading=tr("No transactions yet"),
        placeholder_message=(
            tr("Recording income and expenses with your own categories is coming in the next sprint.")
        ),
    ),
    PageSpec(
        key=BUDGETS_PAGE_KEY,
        nav_label=tr("Budgets"),
        title=tr("Budgets"),
        subtitle=tr("Monthly limits per spending category, compared with this month so far."),
        placeholder_heading=tr("No budgets yet"),
        placeholder_message=tr("Set a monthly limit for a spending category."),
    ),
    PageSpec(
        key=ALLOCATIONS_PAGE_KEY,
        nav_label=tr("Money / Allocations"),
        title=tr("Money / Allocations"),
        subtitle=tr("Set money aside for purposes; what is left is Available to spend."),
        placeholder_heading=tr("Nothing set aside yet"),
        placeholder_message=(
            tr("You will be able to reserve money for savings, bills, investments and more. "
            "Moving money between allocations never changes your total balance.")
        ),
    ),
    PageSpec(
        key=GOALS_PAGE_KEY,
        nav_label=tr("Goals"),
        title=tr("Goals"),
        subtitle=tr("Set financial targets and track your progress."),
        placeholder_heading=tr("No goals yet"),
        placeholder_message=tr("Create savings targets with deadlines and follow your progress."),
    ),
    PageSpec(
        key=SUBSCRIPTIONS_PAGE_KEY,
        nav_label=tr("Subscriptions"),
        title=tr("Subscriptions & Bills"),
        subtitle=tr("Keep recurring payments under control."),
        placeholder_heading=tr("No subscriptions yet"),
        placeholder_message=(
            tr("Track subscriptions and bills, their billing cycles and upcoming due dates.")
        ),
    ),
    PageSpec(
        key=INVESTMENTS_PAGE_KEY,
        nav_label=tr("Investments"),
        title=tr("Investments"),
        subtitle=(tr("Follow your contributions and holdings. Values are entered by you; no "
                  "market data is fetched and no advice is given.")),
        placeholder_heading=tr("No investments yet"),
        placeholder_message=tr("Record contributions to your investments and see how they add up."),
    ),
    PageSpec(
        key=STATISTICS_PAGE_KEY,
        nav_label=tr("Statistics"),
        title=tr("Statistics"),
        subtitle=tr("See whether your spending and saving are improving."),
        placeholder_heading=tr("Charts are on the way"),
        placeholder_message=(
            tr("Category breakdowns, balance trends and month-over-month comparisons will appear here.")
        ),
    ),
    PageSpec(
        key=AI_ADVISOR_PAGE_KEY,
        nav_label=tr("AI Advisor"),
        title=tr("AI Advisor"),
        subtitle=tr("Personalised insights based on your own numbers."),
        placeholder_heading=tr("AI insights are optional"),
        placeholder_message=(
            tr("Choose a local or an online AI provider for insights. Your financial data is never "
            "sent online without your explicit confirmation.")
        ),
    ),
    PageSpec(
        key=SETTINGS_PAGE_KEY,
        nav_label=tr("Settings"),
        title=tr("Settings"),
        subtitle=tr("Preferences and where your data is stored."),
        placeholder_heading=tr("More settings coming"),
        placeholder_message=tr("Currency and appearance options will be added here."),
    ),
)
