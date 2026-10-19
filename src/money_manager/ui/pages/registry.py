"""Single source of truth for the application's pages and their order."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PageSpec:
    key: str
    nav_label: str
    title: str
    subtitle: str
    placeholder_heading: str
    placeholder_message: str


DASHBOARD_PAGE_KEY = "dashboard"
DEFAULT_PAGE_KEY = DASHBOARD_PAGE_KEY
SETTINGS_PAGE_KEY = "settings"
TRANSACTIONS_PAGE_KEY = "transactions"
BUDGETS_PAGE_KEY = "budgets"
STATISTICS_PAGE_KEY = "statistics"
GOALS_PAGE_KEY = "goals"
SUBSCRIPTIONS_PAGE_KEY = "subscriptions"
INVESTMENTS_PAGE_KEY = "investments"
AI_ADVISOR_PAGE_KEY = "ai_advisor"

# Sidebar order; Ctrl+1…9 follow it. Each page's colour lives in ui.theme.PAGE_FILLS.
PAGES: tuple[PageSpec, ...] = (
    PageSpec(
        key=DASHBOARD_PAGE_KEY,
        nav_label="Dashboard",
        title="Dashboard",
        subtitle="Your financial overview at a glance.",
        placeholder_heading="Your overview will live here",
        placeholder_message=(
            "Once you start recording transactions, this page will summarise your balance, "
            "how your money is allocated and how this month compares to the last."
        ),
    ),
    PageSpec(
        key=TRANSACTIONS_PAGE_KEY,
        nav_label="Transactions",
        title="Transactions",
        subtitle="Money that actually enters or leaves your accounts.",
        placeholder_heading="No transactions yet",
        placeholder_message=(
            "Recording income and expenses with your own categories is coming in the next sprint."
        ),
    ),
    PageSpec(
        key=BUDGETS_PAGE_KEY,
        nav_label="Budgets",
        title="Budgets",
        subtitle="Monthly limits per spending category, compared with this month so far.",
        placeholder_heading="No budgets yet",
        placeholder_message="Set a monthly limit for a spending category.",
    ),
    PageSpec(
        key="allocations",
        nav_label="Money / Allocations",
        title="Money / Allocations",
        subtitle="Organise the money you already have into purposes.",
        placeholder_heading="Allocations are on the way",
        placeholder_message=(
            "You will be able to reserve money for savings, bills, investments and more. "
            "Moving money between allocations never changes your total balance."
        ),
    ),
    PageSpec(
        key=GOALS_PAGE_KEY,
        nav_label="Goals",
        title="Goals",
        subtitle="Set financial targets and track your progress.",
        placeholder_heading="No goals yet",
        placeholder_message="Create savings targets with deadlines and follow your progress.",
    ),
    PageSpec(
        key=SUBSCRIPTIONS_PAGE_KEY,
        nav_label="Subscriptions",
        title="Subscriptions & Bills",
        subtitle="Keep recurring payments under control.",
        placeholder_heading="No subscriptions yet",
        placeholder_message=(
            "Track subscriptions and bills, their billing cycles and upcoming due dates."
        ),
    ),
    PageSpec(
        key=INVESTMENTS_PAGE_KEY,
        nav_label="Investments",
        title="Investments",
        subtitle=("Follow your contributions and holdings. Values are entered by you; no "
                  "market data is fetched and no advice is given."),
        placeholder_heading="No investments yet",
        placeholder_message="Record contributions to your investments and see how they add up.",
    ),
    PageSpec(
        key=STATISTICS_PAGE_KEY,
        nav_label="Statistics",
        title="Statistics",
        subtitle="See whether your spending and saving are improving.",
        placeholder_heading="Charts are on the way",
        placeholder_message=(
            "Category breakdowns, balance trends and month-over-month comparisons will appear here."
        ),
    ),
    PageSpec(
        key=AI_ADVISOR_PAGE_KEY,
        nav_label="AI Advisor",
        title="AI Advisor",
        subtitle="Personalised insights based on your own numbers.",
        placeholder_heading="AI insights are optional",
        placeholder_message=(
            "Choose a local or an online AI provider for insights. Your financial data is never "
            "sent online without your explicit confirmation."
        ),
    ),
    PageSpec(
        key=SETTINGS_PAGE_KEY,
        nav_label="Settings",
        title="Settings",
        subtitle="Preferences and where your data is stored.",
        placeholder_heading="More settings coming",
        placeholder_message="Currency and appearance options will be added here.",
    ),
)
