"""Presentation assets: the hero banner and the methodology diagram.

Both are generated from the run record rather than drawn by hand, so the
headline figures on the banner cannot drift away from the numbers the
pipeline actually produced. Re-running the campaign re-renders the banner.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from .economics import value_range

# Palette: dark editorial navy, with a single accent reserved for the north
# star metric so the eye lands on one number.
INK = "#0e1726"
CARD = "#1b2f4e"
CARD_EDGE = "#2f4a66"
ACCENT_BG = "#4a3410"
ACCENT_TEXT = "#f2b544"
HEADLINE = "#ffffff"
SUBHEAD = "#4f93f0"
MUTED = "#93a3b8"

STEP_BLUE = "#2563eb"
STEP_GREEN = "#16a34a"


def build_hero_banner(
    run_record: dict,
    path: Path,
    *,
    title: str = "Campaign Incrementality",
    subtitle: str = "Measurement & Validation Framework",
    caption: str = "How much of a promotion's sales would have happened anyway",
) -> Path:
    """Dark banner with four headline figures, north star highlighted."""
    inc = run_record["incrementality"]
    econ = run_record["economics"]

    # Ranges beside the headline figures: a banner showing only 1.59x invites the
    # reader to take a payback as settled when the calibrated range includes break-even.
    baseline = inc["net_value"] / inc["net_lift"] if inc["net_lift"] else None
    margin = econ["incremental_contribution"] / inc["net_value"] if inc["net_value"] else None
    lift_range = (inc["net_ci_low"], inc["net_ci_high"])
    money = (
        value_range(
            lift_range,
            baseline_bookings=baseline,
            margin_rate=margin,
            total_cost=econ["total_cost"],
        )
        if baseline and margin
        else None
    )
    cards = [
        (f"{int(run_record['n_participants']):,}", "Participating properties", "", False),
        (
            f"{inc['net_lift']:+.1%}",
            "Net incremental lift  (NORTH STAR)",
            f"90% range {lift_range[0]:+.1%} to {lift_range[1]:+.1%}",
            True,
        ),
        (
            f"${inc['net_value'] / 1e6:,.1f}M",
            "Incremental value created",
            f"range ${lift_range[0] * baseline / 1e6:,.1f}M to ${lift_range[1] * baseline / 1e6:,.1f}M"
            if baseline
            else "",
            False,
        ),
        (
            f"{econ['return_on_spend']:.2f}x",
            "Return on campaign spend",
            f"range {money['return_on_spend'][0]:.2f}x to {money['return_on_spend'][1]:.2f}x"
            if money
            else "",
            False,
        ),
    ]

    fig = plt.figure(figsize=(11.2, 3.5), dpi=140)
    fig.patch.set_facecolor(INK)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.045, 0.80, title, color=HEADLINE, fontsize=23, fontweight="bold", va="center")
    ax.text(0.045, 0.635, subtitle, color=SUBHEAD, fontsize=19, fontweight="bold", va="center")
    ax.text(0.045, 0.495, caption, color=MUTED, fontsize=9.5, va="center")

    left, width, gap = 0.045, 0.2175, 0.0125
    for i, (value, label, band, is_star) in enumerate(cards):
        x = left + i * (width + gap)
        ax.add_patch(
            FancyBboxPatch(
                (x, 0.10),
                width,
                0.29,
                boxstyle="round,pad=0.006,rounding_size=0.012",
                facecolor=ACCENT_BG if is_star else CARD,
                edgecolor=ACCENT_TEXT if is_star else CARD_EDGE,
                linewidth=1.0,
                transform=ax.transAxes,
            )
        )
        ax.text(
            x + width / 2,
            0.315,
            value,
            color=ACCENT_TEXT if is_star else HEADLINE,
            fontsize=17,
            fontweight="bold",
            ha="center",
            va="center",
        )
        ax.text(
            x + width / 2,
            0.215,
            label,
            color=MUTED,
            fontsize=7.6,
            ha="center",
            va="center",
        )
        if band:
            ax.text(
                x + width / 2,
                0.135,
                # Two dollar signs in one string switch matplotlib into math mode.
                band.replace("$", r"\$"),
                color=ACCENT_TEXT if is_star else HEADLINE,
                fontsize=7.2,
                ha="center",
                va="center",
            )

    fig.savefig(path, facecolor=INK, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    return path


STEPS = [
    ("Frame", "Define the decision\nand break-even lift"),
    ("Data", "Weekly partner panel,\n18 months of history"),
    ("Yardstick", "Flights, cars, activities\nand market demand"),
    ("Baseline", "Model sales without\nthe campaign"),
    ("Adjust", "Add competitor effect;\ncorrect for last year"),
    ("Validate", "Placebo, stability and\naccuracy checks"),
    ("Decide", "Drivers, economics,\ndecision memo"),
]


def build_methodology_diagram(path: Path) -> Path:
    """Numbered pipeline: the analytical approach at a glance."""
    n = len(STEPS)
    fig, ax = plt.subplots(figsize=(11.2, 2.0), dpi=140)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, n)
    ax.set_ylim(0, 1)
    ax.axis("off")

    for i, (label, detail) in enumerate(STEPS):
        cx = i + 0.5
        final = i == n - 1
        colour = STEP_GREEN if final else STEP_BLUE
        ax.scatter([cx], [0.74], s=980, color=colour, zorder=3)
        ax.text(
            cx,
            0.74,
            str(i + 1),
            color="white",
            fontsize=11.5,
            fontweight="bold",
            ha="center",
            va="center",
            zorder=4,
        )
        ax.text(
            cx,
            0.44,
            label,
            fontsize=9.6,
            fontweight="bold",
            ha="center",
            va="center",
            color="#111827",
        )
        ax.text(
            cx,
            0.19,
            detail,
            fontsize=7.1,
            ha="center",
            va="center",
            color="#6b7280",
            linespacing=1.45,
        )
        if not final:
            ax.annotate(
                "",
                xy=(cx + 0.38, 0.74),
                xytext=(cx + 0.14, 0.74),
                arrowprops={"arrowstyle": "-|>", "color": "#9ca3af", "linewidth": 1.2},
            )

    fig.tight_layout()
    fig.savefig(path, facecolor="white", bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return path


def build_all(run_record_path: Path, figures_dir: Path) -> list[Path]:
    """Render every presentation asset from a completed run."""
    figures_dir.mkdir(parents=True, exist_ok=True)
    record = json.loads(Path(run_record_path).read_text())
    return [
        build_hero_banner(record, figures_dir / "exhibit_a_hero_banner.png"),
        build_methodology_diagram(figures_dir / "exhibit_b_methodology.png"),
    ]
