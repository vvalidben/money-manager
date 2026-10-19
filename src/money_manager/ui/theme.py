"""Visual theme: design tokens (colour, type, spacing) and the application stylesheet.

The look follows the "Money Manager v3" design: a near-black ground, rounded
surface tiles, one lime accent, a pastel colour per page (navigation pill,
header mark, headline tile), Space Grotesk for text and JetBrains Mono for
figures.

Widgets opt into styles through ``objectName`` (e.g. ``Card``, ``NavButton``)
rather than inline ``setStyleSheet`` calls, so the look lives in one place.
Every colour and font size used by the stylesheet is a named token below.
Interactive controls show a visible focus ring for keyboard users.
"""

import logging

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from money_manager.core.resources import resource_path

logger = logging.getLogger(__name__)

ASSETS_DIR = resource_path("ui", "assets")
FONTS_DIR = ASSETS_DIR / "fonts"
FONT_FILES = (
    "SpaceGrotesk-Regular.ttf", "SpaceGrotesk-Medium.ttf", "SpaceGrotesk-SemiBold.ttf",
    "SpaceGrotesk-Bold.ttf",
    "JetBrainsMono-Regular.ttf", "JetBrainsMono-Medium.ttf", "JetBrainsMono-SemiBold.ttf",
)
FONT_FAMILY = "Space Grotesk"
MONO_FONT_FAMILY = "JetBrains Mono"
FALLBACK_FONT_FAMILY = "Segoe UI"
BASE_FONT_POINT_SIZE = 10

# Content width below which paired cards stack instead of sitting side by side.
SIDE_BY_SIDE_MIN_WIDTH = 820


class Colors:
    # Ground and surfaces.
    CONTENT_BG = "#0C0D10"
    SURFACE = "#16181D"  # tiles (cards), inputs, dialogs
    CARD_BG = SURFACE
    RAISED = "#1F2229"  # hover, menus, pressed
    PRESSED = "#262931"

    # Hairlines (white at 6 % / 8 % / 16 % over the surface).
    BORDER = "#22242A"
    INPUT_BORDER = "#2A2C31"
    INPUT_HOVER_BORDER = "#3A3D44"

    TEXT = "#F2F2EF"
    TEXT_SECONDARY = "#C9CAD0"
    TEXT_MUTED = "#9A9CA3"
    TEXT_FAINT = "#6F727A"
    TEXT_DISABLED = "#55585F"
    ON_ACCENT = "#0B0B0D"  # text on any filled colour tile

    # One accent, plus a pastel per page.
    ACCENT = "#C8F169"  # lime
    ACCENT_HOVER = "#DCF79A"
    SKY = "#8ECBFF"
    SUN = "#FFD45C"
    CORAL = "#FF8F6B"
    MINT = "#6EE7B7"
    PINK = "#FFA3D7"
    VIOLET = "#B69CFF"
    ORANGE = "#FFB35C"
    CYAN = "#9FE7FF"
    STONE = "#D6D6D0"

    SIDEBAR_BG = CONTENT_BG
    SIDEBAR_TEXT = TEXT_SECONDARY
    SIDEBAR_HOVER_BG = "rgba(255, 255, 255, 0.05)"
    NAV_ACTIVE_TEXT = ON_ACCENT

    BADGE_BG = ACCENT
    BADGE_TEXT = ON_ACCENT

    PRIMARY = ACCENT
    FOCUS = ACCENT
    # Item-view states must be solid: Qt ignores translucent ::item backgrounds
    # and paints the palette highlight instead (lime 14 %, white 3 % / 1.5 %).
    SELECTION_BG = "#2F3628"
    HOVER_BG = "#1D1F24"
    ALTERNATE_ROW_BG = "#191B20"

    # Money flowing in vs out: positive amounts are mint, the sign (+ / −)
    # carries direction, so outflow keeps the text colour.
    INFLOW = MINT
    OUTFLOW = TEXT

    ERROR_TEXT = "#FF6B6B"
    ERROR_BG = "rgba(255, 107, 107, 0.10)"
    ERROR_BORDER = "rgba(255, 107, 107, 0.35)"

    # Privacy notices (data may leave the computer) wear the advisor's cyan.
    WARNING_TEXT = SUN
    WARNING_BG = "rgba(255, 212, 92, 0.08)"
    WARNING_BORDER = "rgba(255, 212, 92, 0.30)"
    PRIVACY_TEXT = CYAN
    PRIVACY_BG = "rgba(159, 231, 255, 0.07)"
    PRIVACY_BORDER = "rgba(159, 231, 255, 0.30)"

    PROGRESS_TRACK = "#24272D"
    PROGRESS_FILL = ACCENT

    TOOLTIP_BG = TEXT
    # Text and rules on a filled pastel tile (dark ink at 70 % / 12 %).
    TILE_MUTED = "rgba(11, 11, 13, 0.7)"
    TILE_RULE = "rgba(11, 11, 13, 0.12)"
    TOOLTIP_TEXT = ON_ACCENT


# Each page's colour: its navigation pill, header mark and headline tile.
FILL_COLORS = {
    "lime": Colors.ACCENT, "sky": Colors.SKY, "sun": Colors.SUN, "coral": Colors.CORAL,
    "mint": Colors.MINT, "pink": Colors.PINK, "violet": Colors.VIOLET,
    "orange": Colors.ORANGE, "cyan": Colors.CYAN, "stone": Colors.STONE,
}
PAGE_FILLS = {
    "dashboard": "lime", "accounts": "sky", "transactions": "sun", "budgets": "coral",
    "allocations": "mint", "goals": "mint",
    "subscriptions": "pink", "investments": "violet", "statistics": "orange",
    "ai_advisor": "cyan", "settings": "stone",
}


# Identity colours for goals and categories (always shown next to their name).
# The order is fixed and an item keeps its colour by id, so colours never shuffle.
IDENTITY_COLORS = (Colors.MINT, Colors.ACCENT, Colors.SKY, Colors.PINK, Colors.VIOLET,
                   Colors.SUN, Colors.CORAL, Colors.ORANGE, Colors.CYAN)


def identity_color(item_id: int | None) -> str:
    """A stable pastel for a goal or category id; stone for none (e.g. adjustments)."""
    if item_id is None:
        return Colors.STONE
    return IDENTITY_COLORS[(item_id - 1) % len(IDENTITY_COLORS)]


def page_fill(key: str) -> str:
    return PAGE_FILLS.get(key, "lime")


def page_color(key: str) -> str:
    return FILL_COLORS[page_fill(key)]


class FontSize:
    """The type scale, in pixels. The stylesheet uses no other sizes."""

    PAGE_TITLE = 36
    STAT = 28
    STAT_M = 24  # figures step down until they fit their tile
    STAT_COMPACT = 22
    STAT_S = 20
    STAT_XS = 17
    BRAND = 18
    SECTION = 16
    BUTTON = 14
    NAV = 14
    SUBTITLE = 12
    BODY = 13
    SMALL = 12
    CAPTION = 11


class Spacing:
    XS = 4
    SM = 8
    MD = 16
    LG = 24
    XL = 32


def _fill_rules() -> str:
    rules = []
    for name, colour in FILL_COLORS.items():
        rules.append(f"""
    #StatColumn[fill="{name}"] {{
        background-color: {colour};
        border: 1px solid {colour};
    }}""")
        rules.append(f"""
    #NavIndicator[fill="{name}"] {{
        background-color: {colour};
    }}""")
    return "".join(rules)


def build_stylesheet() -> str:
    c, f = Colors, FontSize
    mono = f'"{MONO_FONT_FAMILY}"'
    return f"""
    QWidget {{
        color: {c.TEXT};
    }}
    #ContentArea {{
        background-color: {c.CONTENT_BG};
    }}

    /* Navigation rail */
    #Sidebar {{
        background-color: {c.SIDEBAR_BG};
        border: none;
        border-right: 1px solid {c.BORDER};
    }}
    #BrandMark {{
        background-color: {c.ACCENT};
        color: {c.ON_ACCENT};
        border-radius: 14px;
        font-size: {f.BRAND}px;
        font-weight: 700;
    }}
    #SidebarBrand {{
        font-size: {f.SECTION}px;
        font-weight: 600;
    }}
    #SidebarTagline, #SidebarFooter {{
        color: {c.TEXT_MUTED};
        font-size: {f.CAPTION}px;
    }}
    #SidebarFooter {{
        font-family: {mono};
    }}
    #NavButton {{
        text-align: left;
        padding: 0 14px;
        border: 1px solid transparent;
        border-radius: 14px;
        background-color: transparent;
        color: {c.SIDEBAR_TEXT};
        font-size: {f.NAV}px;
        font-weight: 500;
    }}
    #NavButton:hover {{
        background-color: {c.SIDEBAR_HOVER_BG};
        color: {c.TEXT};
    }}
    #NavButton:checked {{
        background-color: transparent;
        color: {c.NAV_ACTIVE_TEXT};
        font-weight: 600;
    }}
    #NavButton:checked:hover {{
        background-color: transparent;
    }}
    #NavIndicator {{
        border-radius: 14px;
        background-color: {c.ACCENT};
    }}
    #NavButton:focus:!checked {{
        border: 1px solid {c.ACCENT};
    }}

    /* Page header */
    #PageKicker {{
        font-family: {mono};
        font-size: {f.SUBTITLE}px;
        color: {c.TEXT_MUTED};
    }}
    #PageTitle {{
        font-size: {f.PAGE_TITLE}px;
        font-weight: 600;
    }}
    #GlobalSearch {{
        border-radius: 14px;
        padding: 9px 14px;
        font-size: {f.BUTTON}px;
    }}

    /* Tiles */
    #Card, #EmptyState {{
        background-color: {c.SURFACE};
        border: 1px solid {c.BORDER};
        border-radius: 24px;
    }}
    #StatColumn {{
        background-color: {c.SURFACE};
        border: 1px solid {c.BORDER};
        border-radius: 22px;
    }}
    #CardHeading, #EmptyHeading {{
        font-size: {f.SECTION}px;
        font-weight: 600;
    }}
    #CardBody, #FieldLabel {{
        font-size: {f.BODY}px;
        color: {c.TEXT_MUTED};
    }}
    #FieldValue {{
        font-size: {f.BODY}px;
    }}
    #Badge {{
        background-color: {c.BADGE_BG};
        color: {c.BADGE_TEXT};
        border-radius: 10px;
        padding: 3px 10px;
        font-size: {f.CAPTION}px;
        font-weight: 600;
    }}

    #Card:hover, #StatColumn:hover {{
        border-color: {c.INPUT_HOVER_BORDER};
    }}

    /* Confirmation toast */
    #Toast {{
        background-color: {c.RAISED};
        border: 1px solid {c.INPUT_BORDER};
        border-radius: 18px;
    }}
    #ToastCheck {{
        background-color: {c.ACCENT};
        border-radius: 16px;
    }}
    #ToastTitle {{
        font-size: {f.BODY}px;
        font-weight: 600;
    }}
    #ToastDetail {{
        font-family: {mono};
        font-size: {f.SMALL}px;
        color: {c.TEXT_MUTED};
    }}

    /* Renewing soon: a filled pink tile with dark text */
    #RenewingTile {{
        background-color: {c.PINK};
        border: 1px solid {c.PINK};
        border-radius: 24px;
    }}
    #TileHeading {{
        color: {c.ON_ACCENT};
        font-size: {f.SECTION}px;
        font-weight: 600;
    }}
    #TileText {{
        color: {c.ON_ACCENT};
        font-size: {f.BODY}px;
        font-weight: 500;
    }}
    #TileMuted {{
        color: {c.TILE_MUTED};
        font-size: {f.SMALL}px;
    }}
    #TileMuted[overdue="true"] {{
        color: {c.ON_ACCENT};
        font-weight: 700;
    }}
    #TileFigure {{
        color: {c.ON_ACCENT};
        font-family: {mono};
        font-size: {f.BODY}px;
        font-weight: 600;
    }}
    #TileRow {{
        background-color: transparent;
        border: none;
        border-top: 1px solid {c.TILE_RULE};
    }}
    #DayBadge {{
        background-color: {c.ON_ACCENT};
        color: {c.PINK};
        border-radius: 12px;
        font-family: {mono};
        font-size: {f.BODY}px;
        font-weight: 600;
    }}
    #TilePill {{
        background-color: {c.ON_ACCENT};
        color: {c.PINK};
        border: 1px solid {c.ON_ACCENT};
        border-radius: 13px;
        padding: 5px 12px;
        font-size: {f.SMALL}px;
    }}
    #TilePill:hover {{
        background-color: {c.RAISED};
    }}
    #TilePill:focus {{
        border: 1px solid {c.TEXT};
    }}

    /* Inputs */
    QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit {{
        background-color: {c.SURFACE};
        border: 1px solid {c.INPUT_BORDER};
        border-radius: 10px;
        padding: 7px 12px;
        font-size: {f.BODY}px;
        selection-background-color: {c.ACCENT};
        selection-color: {c.ON_ACCENT};
    }}
    QLineEdit:hover, QComboBox:hover, QDateEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover,
    QPlainTextEdit:hover {{
        border: 1px solid {c.INPUT_HOVER_BORDER};
    }}
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
    QPlainTextEdit:focus {{
        border: 1px solid {c.FOCUS};
    }}
    QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled, QSpinBox:disabled,
    QDoubleSpinBox:disabled {{
        color: {c.TEXT_DISABLED};
        border: 1px solid {c.BORDER};
    }}
    QLineEdit[invalid="true"], QComboBox[invalid="true"], QDateEdit[invalid="true"],
    QSpinBox[invalid="true"] {{
        border: 1px solid {c.ERROR_TEXT};
    }}
    QComboBox::drop-down, QDateEdit::drop-down {{
        border: none;
        width: 26px;
    }}
    QComboBox::down-arrow, QDateEdit::down-arrow {{
        image: url("{ASSETS_DIR.as_posix()}/chevron-down.svg");
        width: 12px;
        height: 12px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c.RAISED};
        border: 1px solid {c.INPUT_BORDER};
        selection-background-color: {c.SELECTION_BG};
        selection-color: {c.TEXT};
        outline: none;
        padding: 4px;
    }}

    /* Buttons: rounded tiles; the primary action is filled lime */
    QPushButton, QToolButton {{
        background-color: {c.SURFACE};
        border: 1px solid {c.INPUT_BORDER};
        border-radius: 12px;
        padding: 8px 16px;
        font-size: {f.BUTTON}px;
    }}
    QPushButton:hover, QToolButton:hover {{
        background-color: {c.RAISED};
    }}
    QPushButton:pressed, QToolButton:pressed {{
        background-color: {c.PRESSED};
    }}
    QPushButton:checked {{
        background-color: {c.RAISED};
        border-color: {c.INPUT_HOVER_BORDER};
    }}
    QPushButton:focus, QToolButton:focus {{
        border: 1px solid {c.FOCUS};
    }}
    QPushButton:disabled, QToolButton:disabled {{
        color: {c.TEXT_DISABLED};
        background-color: {c.CONTENT_BG};
        border-color: {c.BORDER};
    }}
    #PrimaryButton {{
        background-color: {c.ACCENT};
        border: 1px solid {c.ACCENT};
        color: {c.ON_ACCENT};
        font-weight: 600;
    }}
    #PrimaryButton:hover {{
        background-color: {c.ACCENT_HOVER};
        border-color: {c.ACCENT_HOVER};
    }}
    #PrimaryButton:pressed {{
        background-color: {c.ACCENT};
    }}
    #PrimaryButton:focus {{
        border: 1px solid {c.TEXT};
    }}
    #PrimaryButton:disabled {{
        background-color: {c.RAISED};
        border-color: {c.RAISED};
        color: {c.TEXT_DISABLED};
    }}
    #DangerButton {{
        color: {c.ERROR_TEXT};
    }}
    #DangerButton:disabled {{
        color: {c.TEXT_DISABLED};
    }}
    #SegmentButton {{
        border-radius: 10px;
        padding: 7px 14px;
        margin-left: 2px;
    }}
    #SegmentButton:checked {{
        background-color: {c.ACCENT};
        border-color: {c.ACCENT};
        color: {c.ON_ACCENT};
        font-weight: 600;
    }}
    QRadioButton, QCheckBox {{
        font-size: {f.BODY}px;
        spacing: 8px;
    }}
    QRadioButton:focus, QCheckBox:focus {{
        color: {c.ACCENT};
    }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {c.INPUT_HOVER_BORDER};
        background-color: {c.SURFACE};
    }}
    QCheckBox::indicator {{
        border-radius: 5px;
    }}
    QRadioButton::indicator {{
        border-radius: 9px;
    }}
    QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
        border-color: {c.ACCENT};
    }}
    QCheckBox::indicator:checked {{
        background-color: {c.ACCENT};
        border-color: {c.ACCENT};
        image: url("{ASSETS_DIR.as_posix()}/check.svg");
    }}
    QRadioButton::indicator:checked {{
        border-color: {c.ACCENT};
        background-color: qradialgradient(cx: 0.5, cy: 0.5, radius: 0.5, fx: 0.5, fy: 0.5,
            stop: 0 {c.ACCENT}, stop: 0.5 {c.ACCENT}, stop: 0.56 {c.SURFACE},
            stop: 1 {c.SURFACE});
    }}
    QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
        border-color: {c.BORDER};
    }}
    QDialog {{
        background-color: {c.SURFACE};
    }}

    /* Tables and lists: rows on the tile, rounded hover */
    QTableView, QListView, QTextBrowser {{
        background-color: transparent;
        alternate-background-color: {c.ALTERNATE_ROW_BG};
        border: 1px solid transparent;
        border-radius: 12px;
        gridline-color: transparent;
        selection-background-color: {c.SELECTION_BG};
        selection-color: {c.TEXT};
        font-size: {f.BODY}px;
    }}
    QTableView:focus, QListView:focus, QTextBrowser:focus {{
        border: 1px solid {c.FOCUS};
    }}
    QTableView::item {{
        padding: 0 6px;
    }}
    QTableView::item:hover {{
        background-color: {c.HOVER_BG};
    }}
    QTableView::item:selected {{
        background-color: {c.SELECTION_BG};
        color: {c.TEXT};
    }}
    QTableView QTableCornerButton::section {{
        background-color: transparent;
        border: none;
    }}
    QListView {{
        background-color: {c.CONTENT_BG};
        border: 1px solid {c.BORDER};
        padding: 4px;
        outline: none;
    }}
    QListView::item {{
        padding: 6px 8px;
        border-radius: 8px;
    }}
    QListView::item:hover {{
        background-color: {c.HOVER_BG};
    }}
    QListView::item:selected {{
        background-color: {c.SELECTION_BG};
        color: {c.TEXT};
    }}
    QTextBrowser {{
        background-color: {c.CONTENT_BG};
        border: 1px solid {c.BORDER};
        padding: 8px;
    }}
    QHeaderView {{
        background-color: transparent;
    }}
    QHeaderView::section {{
        background-color: transparent;
        color: {c.TEXT_MUTED};
        font-size: {f.SMALL}px;
        border: none;
        border-bottom: 1px solid {c.BORDER};
        padding: 8px;
    }}
    QHeaderView::section:hover {{
        color: {c.TEXT};
    }}
    #DataTable {{
        border: 1px solid transparent;
        background-color: transparent;
        alternate-background-color: {c.ALTERNATE_ROW_BG};
    }}
    #DataTable:focus {{
        border: 1px solid {c.FOCUS};
    }}
    #CompactTable {{
        border: none;
        background: transparent;
    }}

    /* Figures: monospaced */
    #StatLabel {{
        font-size: {f.BODY}px;
        font-weight: 500;
        color: {c.TEXT_MUTED};
    }}
    #StatValue {{
        font-family: {mono};
        font-size: {f.STAT}px;
        font-weight: 600;
    }}
    #StatValueCompact {{
        font-family: {mono};
        font-size: {f.STAT_COMPACT}px;
        font-weight: 600;
    }}
    #StatValue[fit="m"], #StatValueCompact[fit="m"] {{
        font-size: {f.STAT_M}px;
    }}
    #StatValue[fit="s"], #StatValueCompact[fit="s"] {{
        font-size: {f.STAT_S}px;
    }}
    #StatValue[fit="xs"], #StatValueCompact[fit="xs"] {{
        font-size: {f.STAT_XS}px;
    }}
    #StatValue[tone="inflow"], #StatValueCompact[tone="inflow"] {{
        color: {c.INFLOW};
    }}
    #StatValue[tone="outflow"], #StatValueCompact[tone="outflow"] {{
        color: {c.OUTFLOW};
    }}
    #StatLabel[onfill="true"], #StatValue[onfill="true"],
    #StatValueCompact[onfill="true"], #MutedLabel[onfill="true"] {{
        color: {c.ON_ACCENT};
    }}
    #MutedLabel {{
        font-size: {f.SMALL}px;
        color: {c.TEXT_MUTED};
    }}
    #FieldError {{
        font-size: {f.SMALL}px;
        color: {c.ERROR_TEXT};
    }}
    #AllocationName, #HealthLabel {{
        font-size: {f.BODY}px;
    }}
    #AllocationAvailable, #AllocationAmount, #HealthValue {{
        font-family: {mono};
        font-size: {f.BODY}px;
        font-weight: 600;
    }}
    #AllocationAmount[tone="outflow"] {{
        color: {c.ERROR_TEXT};
    }}
    #GoalBar, #ShareBar, #ShareBarAvailable {{
        border: none;
        border-radius: 4px;
        background-color: {c.PROGRESS_TRACK};
    }}
    #BudgetBar {{
        border: none;
        border-radius: 4px;
        background-color: {c.PROGRESS_TRACK};
    }}
    #BudgetBar::chunk {{
        border-radius: 4px;
        background-color: {c.MINT};
    }}
    #BudgetBar[level="near_limit"]::chunk {{
        background-color: {c.SUN};
    }}
    #BudgetBar[level="over"]::chunk {{
        background-color: {c.ERROR_TEXT};
    }}
    #GoalBar::chunk, #ShareBar::chunk {{
        border-radius: 4px;
        background-color: {c.PROGRESS_FILL};
    }}
    #ShareBarAvailable::chunk {{
        border-radius: 4px;
        background-color: {c.TEXT_FAINT};
    }}
    #LevelBadge {{
        border-radius: 9px;
        padding: 2px 9px;
        font-size: {f.CAPTION}px;
        font-weight: 600;
        background-color: {c.RAISED};
        color: {c.TEXT_MUTED};
    }}
    #LevelBadge[level="good"] {{
        background-color: {c.MINT};
        color: {c.ON_ACCENT};
    }}
    #LevelBadge[level="fair"] {{
        background-color: {c.SUN};
        color: {c.ON_ACCENT};
    }}
    #LevelBadge[level="poor"] {{
        background-color: {c.ERROR_TEXT};
        color: {c.ON_ACCENT};
    }}

    /* Notices, tooltips and menus */
    #FormError {{
        background-color: {c.ERROR_BG};
        border: 1px solid {c.ERROR_BORDER};
        border-radius: 12px;
        color: {c.ERROR_TEXT};
        padding: 8px 12px;
    }}
    #PrivacyNotice {{
        background-color: {c.PRIVACY_BG};
        border: 1px solid {c.PRIVACY_BORDER};
        border-radius: 12px;
        color: {c.PRIVACY_TEXT};
        padding: 8px 12px;
    }}
    #CautionNotice {{
        background-color: {c.WARNING_BG};
        border: 1px solid {c.WARNING_BORDER};
        border-radius: 12px;
        color: {c.WARNING_TEXT};
        padding: 8px 12px;
    }}
    QToolTip {{
        background-color: {c.TOOLTIP_BG};
        color: {c.TOOLTIP_TEXT};
        border: none;
        border-radius: 10px;
        padding: 6px 10px;
        font-size: {f.SMALL}px;
    }}
    QMenu {{
        background-color: {c.RAISED};
        border: 1px solid {c.INPUT_BORDER};
        border-radius: 12px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 16px;
        border-radius: 8px;
    }}
    QMenu::item:selected {{
        background-color: {c.SELECTION_BG};
        color: {c.TEXT};
    }}

    /* Scrolling */
    QScrollArea, #TransparentArea {{
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {c.INPUT_HOVER_BORDER};
        border-radius: 5px;
        min-height: 32px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c.TEXT_FAINT};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        height: 0;
        background: transparent;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {c.INPUT_HOVER_BORDER};
        border-radius: 5px;
        min-width: 32px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        width: 0;
        background: transparent;
    }}
    {_fill_rules()}
    """


def build_palette() -> QPalette:
    """Colours for what Qt draws natively (message boxes, calendars, spin arrows)."""
    c = Colors
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: c.SURFACE,
        QPalette.ColorRole.WindowText: c.TEXT,
        QPalette.ColorRole.Base: c.SURFACE,
        QPalette.ColorRole.AlternateBase: c.RAISED,
        QPalette.ColorRole.Text: c.TEXT,
        QPalette.ColorRole.Button: c.RAISED,
        QPalette.ColorRole.ButtonText: c.TEXT,
        QPalette.ColorRole.BrightText: c.ACCENT,
        QPalette.ColorRole.Highlight: c.ACCENT,
        QPalette.ColorRole.HighlightedText: c.ON_ACCENT,
        QPalette.ColorRole.ToolTipBase: c.TOOLTIP_BG,
        QPalette.ColorRole.ToolTipText: c.TOOLTIP_TEXT,
        QPalette.ColorRole.PlaceholderText: c.TEXT_FAINT,
        QPalette.ColorRole.Link: c.ACCENT,
        QPalette.ColorRole.LinkVisited: c.ACCENT,
        QPalette.ColorRole.Light: c.INPUT_HOVER_BORDER,
        QPalette.ColorRole.Midlight: c.INPUT_BORDER,
        QPalette.ColorRole.Mid: c.BORDER,
        QPalette.ColorRole.Dark: c.CONTENT_BG,
        QPalette.ColorRole.Shadow: "#000000",
    }
    for role, colour in roles.items():
        palette.setColor(role, QColor(colour))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText,
                 QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(c.TEXT_DISABLED))
    return palette


def load_fonts() -> bool:
    """Register the bundled typefaces; False (and system fonts) if one is missing."""
    loaded = True
    for name in FONT_FILES:
        if QFontDatabase.addApplicationFont(str(FONTS_DIR / name)) < 0:
            logger.warning("Could not load the bundled font %s", name)
            loaded = False
    return loaded


def mono_font(base: QFont | None = None) -> QFont:
    """The figures face (JetBrains Mono), keeping the base font's size and weight."""
    font = QFont(base) if base is not None else QFont()
    font.setFamilies([MONO_FONT_FAMILY, "Consolas"])
    return font


def set_style_property(widget: QWidget, name: str, value: object) -> None:
    """Set a dynamic property used by the stylesheet and re-apply the style."""
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    family = FONT_FAMILY if load_fonts() else FALLBACK_FONT_FAMILY
    app.setFont(QFont(family, BASE_FONT_POINT_SIZE))
    app.setPalette(build_palette())
    app.setStyleSheet(build_stylesheet())
