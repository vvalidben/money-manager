"""Shared chart infrastructure: styled Matplotlib canvas, chart card, palette.

Chart rules (see the dataviz guidelines): thin marks, hairline solid grid,
recessive axes, a legend only for two or more series, selective direct
labels, text in text colours (never the series colour), and a table view for
every chart so no value is reachable only by hovering.

Money is converted to ``float`` here *only* to position marks on screen;
every number shown as text is formatted from the exact ``Money`` value.
"""

import logging
import warnings
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import matplotlib
from matplotlib import font_manager
from matplotlib.backend_bases import MouseEvent
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MaxNLocator
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolTip,
    QWidget,
)

from money_manager.domain.money import Money
from money_manager.ui.components.card import Card
from money_manager.ui.formatting import format_compact_amount
from money_manager.ui.theme import FONT_FAMILY, FONT_FILES, FONTS_DIR, Colors, Spacing

# Categorical slots in their fixed order: a lime step of the design's accent,
# then violet, orange, blue and yellow. Validated as a set on the dark ground
# (#0c0d10): lightness band, chroma, adjacent CVD ΔE ≥ 8 and normal-vision
# ΔE ≥ 15, contrast ≥ 3:1. (The design's pastels are too light for marks.)
CATEGORICAL = (Colors.CHART_FIRST, "#9085e9", "#d95926", "#3987e5", "#c98500")
# Income vs expenses: the blue/orange pair, separable with every colour vision.
INCOME_COLOR = "#3987e5"
EXPENSE_COLOR = "#d95926"
BALANCE_COLOR = Colors.CHART_LINE  # the single balance line wears the accent, as in the design
PREVIOUS_COLOR = "#1c5cab"  # a darker step of the income blue ("before" next to "after")
# Neutral chart ink comes from the theme so charts match the rest of the UI.
OTHER_COLOR = Colors.TEXT_FAINT  # de-emphasis grey for folded "Other" slices
GRID_COLOR = Colors.CHART_GRID
AXIS_COLOR = Colors.INPUT_HOVER_BORDER
INK_MUTED = Colors.TEXT_MUTED
INK_SECONDARY = Colors.TEXT_SECONDARY
SURFACE = Colors.SURFACE  # charts sit on tiles

for _font in FONT_FILES:
    if (FONTS_DIR / _font).is_file():
        font_manager.fontManager.addfont(str(FONTS_DIR / _font))
# Fallback families lack some weights; matplotlib substitutes the nearest one
# and would log that on every draw.
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

matplotlib.rcParams.update(
    {
        "font.family": [FONT_FAMILY, "Segoe UI", "DejaVu Sans"],
        "font.size": 9,
        "axes.edgecolor": AXIS_COLOR,
        "axes.labelcolor": INK_MUTED,
        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,
        "text.color": INK_SECONDARY,
    }
)

# While a window is being resized a chart can briefly be too small to lay out;
# Matplotlib then keeps the previous layout, which is fine, but warns each time.
warnings.filterwarnings("ignore", message="constrained_layout not applied")

MIN_CHART_WIDTH = 200

TableData = tuple[list[str], list[list[str]]]


def plot_value(value: Money) -> float:
    """Screen position only; never used for arithmetic."""
    return float(value.amount)


def money_axis(axis: Any) -> None:
    axis.set_major_locator(MaxNLocator(nbins=4))
    axis.set_major_formatter(
        FuncFormatter(lambda value, _pos: format_compact_amount(Decimal(str(round(value)))))
    )


@dataclass(frozen=True, slots=True)
class _HoverTarget:
    contains: Any  # callable(event) -> bool
    text: str


class ChartCanvas(FigureCanvasQTAgg):
    """A figure with one styled axes, hover tooltips and an empty-state message."""

    def __init__(self, height_px: int = 240) -> None:
        self.figure = Figure(facecolor=SURFACE, layout="constrained")
        super().__init__(self.figure)
        self.axes = self.figure.add_subplot()
        self.setMinimumHeight(height_px)
        self.setMaximumHeight(height_px)
        self.setMinimumWidth(MIN_CHART_WIDTH)
        self._targets: list[_HoverTarget] = []
        self.mpl_connect("motion_notify_event", self._on_hover)
        self.mpl_connect("figure_leave_event", lambda _event: QToolTip.hideText())

    def reset(self) -> None:
        self.axes.clear()
        self._targets = []
        ax = self.axes
        ax.set_facecolor(SURFACE)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(AXIS_COLOR)
        ax.spines["bottom"].set_linewidth(1)
        ax.tick_params(length=0, pad=6)
        ax.grid(axis="y", color=GRID_COLOR, linewidth=1, linestyle="-")
        ax.set_axisbelow(True)

    def show_message(self, message: str) -> None:
        self.reset()
        self.axes.grid(False)
        self.axes.spines["bottom"].set_visible(False)
        self.axes.set_xticks([])
        self.axes.set_yticks([])
        self.axes.text(0.5, 0.5, message, ha="center", va="center", color=INK_MUTED,
                       transform=self.axes.transAxes)
        self.draw_idle()

    def add_hover(self, artist: Any, text: str) -> None:
        self._targets.append(_HoverTarget(artist.contains, text))

    @property
    def hover_texts(self) -> list[str]:
        return [target.text for target in self._targets]

    def hover_text(self, event: MouseEvent) -> str | None:
        """Tooltip for the mark under the mouse; subclasses may override."""
        for target in self._targets:
            hit, _details = target.contains(event)
            if hit:
                return target.text
        return None

    def _on_hover(self, event: MouseEvent) -> None:
        text = self.hover_text(event)
        if text:
            QToolTip.showText(QCursor.pos(), text, self)
        else:
            QToolTip.hideText()


class ChartCard(Card):
    """A titled card holding a chart and its table view, with a toggle between them."""

    def __init__(self, title: str, subtitle: str, chart: ChartCanvas,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.chart = chart

        heading = QLabel(title)
        heading.setObjectName("CardHeading")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("MutedLabel")
        self.subtitle_label.setWordWrap(True)
        self.toggle_button = QPushButton("Table")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setToolTip("Show the values as a table")
        self.toggle_button.setAccessibleName(f"Show {title} as a table")
        self.setAccessibleName(title)
        self.toggle_button.toggled.connect(self._on_toggled)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(heading)
        header_layout.addStretch(1)
        header_layout.addWidget(self.toggle_button)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(chart.minimumHeight())
        self.table.setMaximumHeight(chart.maximumHeight())

        self.stack = QStackedWidget()
        self.stack.addWidget(chart)
        self.stack.addWidget(self.table)

        self.body.setSpacing(Spacing.XS)
        self.body.addWidget(header)
        self.body.addWidget(self.subtitle_label)
        self.body.addWidget(self.stack)

    def set_table(self, data: TableData) -> None:
        headers, rows = data
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setRowCount(len(rows))
        self.table.setHorizontalHeaderLabels(headers)
        for row_index, row in enumerate(rows):
            for column, text in enumerate(row):
                item = QTableWidgetItem(text)
                if column > 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row_index, column, item)

    def _on_toggled(self, show_table: bool) -> None:
        self.stack.setCurrentIndex(1 if show_table else 0)
        self.toggle_button.setText("Chart" if show_table else "Table")
