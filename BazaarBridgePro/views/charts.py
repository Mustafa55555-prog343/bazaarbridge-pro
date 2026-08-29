"""
views/charts.py
================================================================================
Helpers that build matplotlib figures (styled to match the app theme) and embed
them inside Tk frames. Used by the Seller, Delivery and Admin dashboards for the
revenue, category, city, growth and forecast charts.

Design goals:
  * Every chart carries clear, labelled axes (units on the value axis, a label
    on the category/time axis).
  * Clean, premium styling — no top/right spines, a light horizontal grid only,
    money formatted with thousands separators (e.g. 100k, 1.2M).
  * Donut/pie charts never overlap their percentage labels: only slices large
    enough to fit a label are annotated on the ring, and a full legend (with the
    exact share) keeps every category identifiable.
================================================================================
"""

import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter, MaxNLocator

from utils.theme import COLORS, apply_matplotlib_style

apply_matplotlib_style()

# A refined, evenly-spaced categorical palette for pies / donuts.
PIE_COLORS = ["#4f46e5", "#10b981", "#0ea5e9", "#f59e0b", "#ef4444",
              "#8b5cf6", "#ec4899", "#14b8a6", "#6366f1", "#f97316",
              "#22c55e", "#06b6d4", "#a855f7", "#eab308", "#84cc16"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _embed(master, fig):
    """Embed a matplotlib Figure into `master` and return the canvas widget."""
    canvas = FigureCanvasTkAgg(fig, master=master)
    canvas.draw()
    widget = canvas.get_tk_widget()
    widget.pack(fill="both", expand=True)
    return widget


def _money_fmt(value, _pos=None):
    """Format an axis value compactly without producing duplicate labels.

    Whole thousands render as 1k / 2k; half-thousands keep one decimal (1.5k)
    so adjacent ticks never collapse to the same text.
    """
    a = abs(value)
    if a >= 1_000_000:
        return f"{value / 1_000_000:.1f}M".replace(".0M", "M")
    if a >= 1_000:
        return f"{value / 1_000:.1f}k".replace(".0k", "k")
    return f"{value:.0f}"


def _empty(ax):
    """Render a tidy 'no data' placeholder."""
    ax.text(0.5, 0.5, "No data yet", ha="center", va="center",
            transform=ax.transAxes, color=COLORS["muted"], fontsize=10)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


def _clean(ax, money_axis=None, grid_axis="y"):
    """Strip top/right spines, keep a light grid on one axis, format money."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLORS["border_d"])
    ax.spines["bottom"].set_color(COLORS["border_d"])
    ax.grid(axis="x", visible=(grid_axis == "x"))
    ax.grid(axis="y", visible=(grid_axis == "y"))
    ax.tick_params(length=0)
    # Choose 'nice' round tick values (e.g. 0, 1k, 2k, 3k) so compact labels
    # never round to the same text on adjacent ticks.
    nice = MaxNLocator(nbins=6, steps=[1, 2, 2.5, 5, 10], min_n_ticks=4)
    if money_axis == "y":
        ax.yaxis.set_major_locator(nice)
        ax.yaxis.set_major_formatter(FuncFormatter(_money_fmt))
    elif money_axis == "x":
        ax.xaxis.set_major_locator(nice)
        ax.xaxis.set_major_formatter(FuncFormatter(_money_fmt))


def _is_money(label):
    return bool(label) and label.strip().lower().startswith("rs")


def _time_ticks(ax, labels):
    """Show ~8 evenly-spaced, readable tick labels for a time series."""
    n = len(labels)
    if n == 0:
        return
    target = 8
    step = max(1, n // target)
    idx = list(range(0, n, step))
    # Always include the final point, but if it sits too close to the previous
    # tick, replace that tick instead of appending (prevents label overlap).
    if idx[-1] != n - 1:
        if (n - 1) - idx[-1] >= max(1, step // 2):
            idx.append(n - 1)
        else:
            idx[-1] = n - 1
    ax.set_xticks(idx)
    short = [str(labels[i]) for i in idx]
    rot = 0 if max((len(s) for s in short), default=0) <= 5 else 30
    ax.set_xticklabels(short, rotation=rot, ha=("center" if rot == 0 else "right"),
                       fontsize=8)


# ---------------------------------------------------------------------------
# Line chart
# ---------------------------------------------------------------------------
def line_chart(master, x, y, title="", ylabel="Rs", xlabel="Date",
               color=None, size=(5.8, 3.0)):
    """Filled line chart (e.g. revenue over time). `x` holds display labels."""
    color = color or COLORS["primary"]
    fig = Figure(figsize=size, dpi=100)
    ax = fig.add_subplot(111)
    if x and y:
        xs = range(len(x))
        ax.plot(xs, y, color=color, linewidth=2.4, marker="o", markersize=3.5,
                markerfacecolor=color, markeredgecolor="white",
                markeredgewidth=0.6, zorder=3)
        ax.fill_between(xs, y, color=color, alpha=0.10, zorder=2)
        ax.set_ylim(bottom=0)
        ax.margins(x=0.02)
        _time_ticks(ax, x)
        _clean(ax, money_axis="y" if _is_money(ylabel) else None)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=9, color=COLORS["text_soft"])
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=9, color=COLORS["text_soft"])
    else:
        _empty(ax)
    if title:
        ax.set_title(title, loc="left", pad=10)
    fig.tight_layout(pad=1.3)
    return _embed(master, fig)


# ---------------------------------------------------------------------------
# Bar chart
# ---------------------------------------------------------------------------
def bar_chart(master, labels, values, title="", ylabel="", xlabel="",
              color=None, size=(5.8, 3.0), horizontal=False):
    """Bar chart (category revenue, top sellers, etc.) with labelled axes."""
    color = color or COLORS["info"]
    fig = Figure(figsize=size, dpi=100)
    ax = fig.add_subplot(111)
    if labels and values:
        if horizontal:
            ypos = range(len(labels))
            bars = ax.barh(ypos, values, color=color, height=0.66, zorder=3)
            ax.set_yticks(list(ypos))
            ax.set_yticklabels([str(l) for l in labels], fontsize=8.5)
            ax.invert_yaxis()
            ax.margins(y=0.02)
            _clean(ax, money_axis="x" if _is_money(xlabel) else None, grid_axis="x")
            # Annotate each bar with its value just past the bar end — a clean,
            # professional touch that makes the chart readable at a glance.
            vmax = max(values) if values else 0
            ax.set_xlim(0, vmax * 1.18 if vmax else 1)
            money = _is_money(xlabel)
            for rect, val in zip(bars, values):
                label = (f"Rs {val:,.0f}" if money else f"{val:,.0f}")
                ax.text(rect.get_width() + vmax * 0.015,
                        rect.get_y() + rect.get_height() / 2, label,
                        va="center", ha="left", fontsize=8,
                        color=COLORS["text_soft"])
            if xlabel:
                ax.set_xlabel(xlabel, fontsize=9, color=COLORS["text_soft"])
            if ylabel:
                ax.set_ylabel(ylabel, fontsize=9, color=COLORS["text_soft"])
        else:
            xpos = range(len(labels))
            ax.bar(xpos, values, color=color, width=0.62, zorder=3)
            ax.set_xticks(list(xpos))
            rot = 0 if max((len(str(l)) for l in labels), default=0) <= 4 else 30
            ax.set_xticklabels([str(l) for l in labels], rotation=rot,
                               ha=("center" if rot == 0 else "right"), fontsize=8)
            ax.set_ylim(bottom=0)
            _clean(ax, money_axis="y" if _is_money(ylabel) else None)
            if ylabel:
                ax.set_ylabel(ylabel, fontsize=9, color=COLORS["text_soft"])
            if xlabel:
                ax.set_xlabel(xlabel, fontsize=9, color=COLORS["text_soft"])
    else:
        _empty(ax)
    if title:
        ax.set_title(title, loc="left", pad=10)
    fig.tight_layout(pad=1.3)
    return _embed(master, fig)


# ---------------------------------------------------------------------------
# Donut / pie chart
# ---------------------------------------------------------------------------
def pie_chart(master, labels, values, title="", size=(6.0, 3.2)):
    """
    Donut chart (orders by category / city distribution).

    To avoid the classic overlapping-label problem on small slices, only slices
    that are large enough to comfortably fit a label (>= 6%) are annotated on the
    ring; the legend lists every category with its exact share so nothing is lost.
    """
    fig = Figure(figsize=size, dpi=100)
    ax = fig.add_subplot(111)
    total = sum(values) if values else 0
    if labels and values and total > 0:
        colors = [PIE_COLORS[i % len(PIE_COLORS)] for i in range(len(labels))]
        shares = [v / total * 100 for v in values]

        def _autopct(pct):
            return f"{pct:.0f}%" if pct >= 6 else ""

        wedges, _texts, autotexts = ax.pie(
            values, labels=None, autopct=_autopct, startangle=90,
            colors=colors, pctdistance=0.78, counterclock=False,
            wedgeprops=dict(width=0.40, edgecolor="white", linewidth=1.5),
            textprops=dict(color="white", fontsize=8.5, fontweight="bold"))
        ax.axis("equal")

        # Legend with exact shares, placed to the right with breathing room.
        legend_labels = [f"{lab}  ·  {sh:.0f}%" for lab, sh in zip(labels, shares)]
        ax.legend(wedges, legend_labels, loc="center left",
                  bbox_to_anchor=(1.02, 0.5), fontsize=8.5, frameon=False,
                  handlelength=1.1, handleheight=1.1, labelspacing=0.6,
                  borderaxespad=0)
    else:
        _empty(ax)
    if title:
        ax.set_title(title, loc="left", pad=10)
    # Leave room on the right for the legend.
    fig.subplots_adjust(left=0.02, right=0.62, top=0.90, bottom=0.06)
    return _embed(master, fig)


# ---------------------------------------------------------------------------
# Forecast chart
# ---------------------------------------------------------------------------
def forecast_chart(master, history_days, history_vals, forecast_vals,
                   title="Revenue Forecast", ylabel="Rs", xlabel="Day",
                   size=(5.8, 3.0)):
    """Line chart showing actual revenue plus a dashed forecast tail."""
    fig = Figure(figsize=size, dpi=100)
    ax = fig.add_subplot(111)
    n = len(history_vals)
    if n:
        ax.plot(range(n), history_vals, color=COLORS["primary"], linewidth=2.4,
                marker="o", markersize=3, label="Actual", zorder=3)
        fx = range(n - 1, n - 1 + len(forecast_vals) + 1)
        fy = [history_vals[-1]] + list(forecast_vals)
        ax.plot(list(fx), fy, color=COLORS["warning"], linewidth=2.4,
                linestyle="--", marker="o", markersize=3, label="Forecast",
                zorder=3)
        ax.fill_between(range(n), history_vals, color=COLORS["primary"],
                        alpha=0.08, zorder=1)
        ax.set_ylim(bottom=0)
        ax.margins(x=0.02)
        _clean(ax, money_axis="y" if _is_money(ylabel) else None)
        ax.legend(fontsize=8.5, frameon=False, loc="upper left")
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=9, color=COLORS["text_soft"])
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=9, color=COLORS["text_soft"])
    else:
        _empty(ax)
    if title:
        ax.set_title(title, loc="left", pad=10)
    fig.tight_layout(pad=1.3)
    return _embed(master, fig)
