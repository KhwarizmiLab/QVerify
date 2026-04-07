import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.transforms as mtransforms
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, FuncFormatter, MultipleLocator

from qverify_simulation.config import CHSH_REL_ERR_THRESHOLD_PCT
from qverify_simulation.figures.style import (
    FIG_HEIGHT_REL_ERR,
    FIG_WIDTH_IN_SINGLE_COL,
    PAPER_RC,
    _COLOR_ATTACK,
    _COLOR_DANGER,
    _COLOR_HONEST,
    _COLOR_SAFE,
    _COLOR_THRESH,
)

# Fraction of horizontal axis devoted to the secure (green) band in display space [0,1].
# The Eve (red) band uses the remainder; smaller values tighten green-band bar spacing
# and give the (typically more populated) red band more room.
_W_GREEN_DISPLAY_FRAC = 0.40

# "Secure" / "Eve detected" sit at axes y=0.78 with va="top". Require
# ymax_bar / y_lim_hi <= this so bar tops do not overlap the label glyphs.
_MAX_BAR_TOP_FRAC_FOR_BAND_LABELS = 0.68

# Bar width in display space (u): each bin has two bars of width w meeting at u, so
# 2*w <= min adjacent bin spacing; cap is just below 0.5 for safety.
_BAR_CAP_FRAC_OF_MIN_DELTA = 0.4999
# Scales physical-error width into u; higher → wider bars until the cap binds.
_BAR_W_FRAC_OF_GAP = 0.65


def _y_lim_hi_from_ymax(ymax_bar: float, y_tick_step: int = 10) -> int:
    """Upper y (probability %) limit: tight scale but room below band labels."""
    ymax_bar = float(max(ymax_bar, 1e-9))
    y_lim_hi = int((int(ymax_bar // y_tick_step) + 1) * y_tick_step)
    y_lim_hi = max(y_lim_hi, int(np.ceil(ymax_bar)))
    min_for_labels = int(
        np.ceil(ymax_bar / _MAX_BAR_TOP_FRAC_FOR_BAND_LABELS / y_tick_step) * y_tick_step
    )
    return max(y_lim_hi, min_for_labels)


def _x_to_u_piecewise(x, x_lim_lo, x_lim_hi, threshold, w_green):
    """Map physical error (%) to display coordinate u in [0, 1]."""
    w_red = 1.0 - w_green
    x = np.asarray(x, dtype=float)
    u = np.empty_like(x, dtype=float)
    left = x <= threshold
    u[left] = (x[left] - x_lim_lo) / (threshold - x_lim_lo) * w_green
    u[~left] = w_green + (x[~left] - threshold) / (x_lim_hi - threshold) * w_red
    return u


def _u_to_x_piecewise(u, x_lim_lo, x_lim_hi, threshold, w_green):
    """Inverse of _x_to_u_piecewise."""
    w_red = 1.0 - w_green
    u = np.asarray(u, dtype=float)
    x = np.empty_like(u, dtype=float)
    left = u <= w_green
    x[left] = x_lim_lo + u[left] / w_green * (threshold - x_lim_lo)
    x[~left] = threshold + (u[~left] - w_green) / w_red * (x_lim_hi - threshold)
    return x


def _du_dx_piecewise(x, x_lim_lo, x_lim_hi, threshold, w_green):
    """Derivative du/dx for bar width scaling in display space."""
    w_red = 1.0 - w_green
    x = np.asarray(x, dtype=float)
    s = np.empty_like(x, dtype=float)
    left = x <= threshold
    s[left] = w_green / (threshold - x_lim_lo)
    s[~left] = w_red / (x_lim_hi - threshold)
    return s


def _piecewise_xticks(
    x_lim_lo: float,
    x_lim_hi: float,
    threshold: float,
    w_green: float,
    *,
    min_u_sep: float = 0.080,   # raised from 0.072 — safer at 3.5 in single-column
    left_step: float = 5.0,
    max_red_ticks: int = 4,
) -> np.ndarray:
    """Choose x-axis tick values (percent) with fewer labels in the compressed red band."""
    red_span = x_lim_hi - threshold
    step_red = max(10.0, float(np.ceil(red_span / max(1, max_red_ticks - 1) / 5.0) * 5.0))

    lo0 = np.floor(x_lim_lo / left_step) * left_step
    left_edges = np.arange(lo0, threshold + 0.49 * left_step, left_step)
    left_edges = left_edges[(left_edges >= x_lim_lo - 1e-9) & (left_edges <= threshold + 1e-9)]

    right_edges = np.arange(threshold, x_lim_hi + 0.49 * step_red, step_red)
    right_edges = right_edges[(right_edges >= threshold - 1e-9) & (right_edges <= x_lim_hi + 1e-9)]

    candidates = np.unique(np.concatenate([left_edges, right_edges]))
    candidates = candidates[(candidates >= x_lim_lo - 1e-9) & (candidates <= x_lim_hi + 1e-9)]

    u_vals = _x_to_u_piecewise(candidates, x_lim_lo, x_lim_hi, threshold, w_green)
    order = np.argsort(u_vals)
    picked: list[float] = []
    last_u = -np.inf
    for idx in order:
        uu = float(u_vals[idx])
        xc = float(candidates[idx])
        at_thr = abs(xc - threshold) < 1e-6
        if at_thr or uu - last_u >= min_u_sep:
            picked.append(xc)
            last_u = uu

    if x_lim_lo <= threshold <= x_lim_hi and not any(abs(p - threshold) < 1e-6 for p in picked):
        u_thr = float(_x_to_u_piecewise(np.array([threshold]), x_lim_lo, x_lim_hi, threshold, w_green)[0])
        u_picked = _x_to_u_piecewise(np.array(picked), x_lim_lo, x_lim_hi, threshold, w_green)
        if len(picked) == 0 or np.min(np.abs(u_picked - u_thr)) >= min_u_sep * 0.9:
            picked.append(threshold)

    return np.array(sorted(set(picked)), dtype=float)


def _bar_width_u_uniform(bar_w: float, dudx: np.ndarray, u_centers: np.ndarray) -> float:
    """Uniform bar half-width in u: maximize width subject to no overlap between bins.

    Each x-bin has two bars meeting at u; the pair spans 2*w in u, so w <= 0.5 * min gap.
    """
    raw = bar_w * np.asarray(dudx, dtype=float)
    u_sorted = np.sort(np.unique(u_centers))
    if len(u_sorted) > 1:
        min_delta = float(np.min(np.diff(u_sorted)))
        return float(_BAR_CAP_FRAC_OF_MIN_DELTA * min_delta)
    cap_u = float(np.max(raw)) * 2.0
    med = float(np.median(raw))
    floor_u = max(med * 0.5, float(np.percentile(raw, 20)))
    lo = min(floor_u, cap_u)
    return float(np.clip(float(np.median(raw)), lo, cap_u))


def _figure_layout(
    dist_attack: dict,
    dist_honest: dict,
    threshold: float = CHSH_REL_ERR_THRESHOLD_PCT,
) -> tuple[float, int]:
    """Compute (bar_w_u, y_lim_hi) for one figure without rendering it.

    Separating layout from rendering lets callers harmonise both values across
    fig1 and fig2 before either figure is drawn.
    """
    all_vals = sorted(set(dist_attack.keys()) | set(dist_honest.keys()))
    x = np.array(all_vals, dtype=float)
    p_atk = np.array([dist_attack.get(v, 0) * 100 for v in all_vals])
    p_hon = np.array([dist_honest.get(v, 0) * 100 for v in all_vals])
    gaps = np.diff(x) if len(x) > 1 else np.array([5.0])
    bar_w = max(1.5, _BAR_W_FRAC_OF_GAP * gaps.min())
    x_data_hi = float(max(x.max(), threshold)) if len(x) else float(threshold)
    x_span = max(x_data_hi, 1.0)
    x_lim_lo = -(max(3.0, 0.06 * x_span))
    x_lim_hi = x_data_hi + max(8.0, 0.06 * x_span)
    w_g = _W_GREEN_DISPLAY_FRAC
    u = _x_to_u_piecewise(x, x_lim_lo, x_lim_hi, threshold, w_g)
    dudx = _du_dx_piecewise(x, x_lim_lo, x_lim_hi, threshold, w_g)
    bar_w_u = _bar_width_u_uniform(bar_w, dudx, u)
    ymax_bar = float(max(p_atk.max(), p_hon.max(), 1e-9))
    y_lim_hi = _y_lim_hi_from_ymax(ymax_bar)
    return bar_w_u, y_lim_hi


def aligned_layout(
    dist_attack1: dict,
    dist_attack2: dict,
    dist_honest: dict,
    threshold: float = CHSH_REL_ERR_THRESHOLD_PCT,
) -> tuple[float, int]:
    """Return (bar_w_u, y_lim_hi) shared by both relative-error figures.

    ``bar_w_u`` is the minimum of each figure's natural width so both use the
    same bar thickness in display coordinates (the tighter of the two bin
    spacings) and stay visually in sync. ``y_lim_hi`` is the maximum ceiling so
    neither plot clips.

    Pass the same ``bar_w_u`` and ``y_lim_hi`` to ``plot_fig1_imr`` and
    ``plot_fig2_v1``. Figure size is fixed in ``_plot_error_fig`` via
    ``FIG_WIDTH_IN_SINGLE_COL`` / ``FIG_HEIGHT_REL_ERR``.
    """
    bw1, yl1 = _figure_layout(dist_attack1, dist_honest, threshold)
    bw2, yl2 = _figure_layout(dist_attack2, dist_honest, threshold)
    return min(bw1, bw2), max(yl1, yl2)


def _plot_error_fig(
    dist_attack,
    dist_honest,
    label_attack,
    label_honest,
    title,           # retained for API compatibility; not drawn — put title in caption
    output_file,
    threshold=CHSH_REL_ERR_THRESHOLD_PCT,
    *,
    bar_w_u: float | None = None,   # pass from aligned_layout() or _figure_layout
    y_lim_hi: int | None = None,    # pass from aligned_layout() for shared y scale
    omit_x_ticks: tuple[float, ...] = (),
):
    all_vals = sorted(set(dist_attack.keys()) | set(dist_honest.keys()))
    x = np.array(all_vals, dtype=float)
    p_atk = np.array([dist_attack.get(v, 0) * 100 for v in all_vals])
    p_hon = np.array([dist_honest.get(v, 0) * 100 for v in all_vals])
    gaps = np.diff(x) if len(x) > 1 else np.array([5.0])
    bar_w = max(1.5, _BAR_W_FRAC_OF_GAP * gaps.min())
    x_data_hi = float(max(x.max(), threshold)) if len(x) else float(threshold)
    x_span = max(x_data_hi, 1.0)
    x_pad = max(3.0, 0.06 * x_span)
    x_lim_lo = -x_pad
    x_lim_hi = x_data_hi + max(8.0, 0.06 * x_span)
    w_g = _W_GREEN_DISPLAY_FRAC
    u_pad = 0.02
    u_lim_lo = -u_pad
    u_lim_hi = 1.0 + u_pad

    y_tick_step = 10
    if y_lim_hi is None:
        ymax_bar = float(max(p_atk.max(), p_hon.max(), 1e-9))
        y_lim_hi = _y_lim_hi_from_ymax(ymax_bar)

    u = _x_to_u_piecewise(x, x_lim_lo, x_lim_hi, threshold, w_g)
    dudx = _du_dx_piecewise(x, x_lim_lo, x_lim_hi, threshold, w_g)
    if bar_w_u is None:
        bar_w_u = _bar_width_u_uniform(bar_w, dudx, u)

    x_ticks = _piecewise_xticks(x_lim_lo, x_lim_hi, threshold, w_g)
    if omit_x_ticks:
        x_ticks = np.array(
            [
                t
                for t in x_ticks
                if not any(abs(float(t) - o) < 1e-6 for o in omit_x_ticks)
            ],
            dtype=float,
        )
    u_ticks = np.unique(
        np.round(_x_to_u_piecewise(x_ticks, x_lim_lo, x_lim_hi, threshold, w_g), decimals=10)
    )

    def _fmt_x_from_u(v, _pos):
        xv = float(_u_to_x_piecewise(v, x_lim_lo, x_lim_hi, threshold, w_g))
        if abs(xv) < 1e-6:
            xv = 0.0
        if abs(xv - round(xv)) < 1e-5:
            return f"{xv:.0f}"
        return f"{xv:.1f}"

    with plt.rc_context(PAPER_RC):
        fig, ax = plt.subplots(figsize=(FIG_WIDTH_IN_SINGLE_COL, FIG_HEIGHT_REL_ERR))
        # blended transform: x in display (u), y in axes fraction
        x_y_text = mtransforms.blended_transform_factory(ax.transData, ax.transAxes)

        # Muted background bands — low alpha so bars are dominant
        ax.axvspan(u_lim_lo, w_g, alpha=0.07, color=_COLOR_SAFE, zorder=0, linewidth=0)
        ax.axvspan(w_g, u_lim_hi, alpha=0.07, color=_COLOR_DANGER, zorder=0, linewidth=0)

        # Threshold line: dashed, distinct but not dominant
        ax.axvline(
            w_g,
            color=_COLOR_THRESH,
            linestyle=(0, (4, 3)),
            linewidth=1.0,
            zorder=2,
        )

        _edge = "0.2"
        # No bar edges: paired bars meet at u; stroked edges double at the join and read as a gap.
        ax.bar(
            u - bar_w_u / 2,
            p_atk,
            bar_w_u,
            color=_COLOR_ATTACK,
            edgecolor="none",
            label=label_attack,
            alpha=0.95,
            zorder=3,
        )
        ax.bar(
            u + bar_w_u / 2,
            p_hon,
            bar_w_u,
            color=_COLOR_HONEST,
            edgecolor="none",
            label=label_honest,
            alpha=0.95,
            zorder=3,
        )

        ax.set_xlabel(
            "Relative CHSH error "
            r"$|S - S_{\mathrm{ideal}}|/|S_{\mathrm{ideal}}|$ (%)"
            "\n"
            r"with $S_{\mathrm{ideal}} = -2\sqrt{2}$",
            labelpad=6,
            ha="center",
        )
        ax.set_ylabel("Outcome Probability (%)", labelpad=5)
        # Title omitted — use figure caption (caption-first style).

        ax.set_xlim(u_lim_lo, u_lim_hi)
        ax.set_ylim(0, y_lim_hi)

        ax.xaxis.set_major_locator(FixedLocator(u_ticks))
        ax.xaxis.set_major_formatter(FuncFormatter(_fmt_x_from_u))
        ax.tick_params(axis="x", labelsize=8, pad=3, length=3.5, width=0.75)
        ax.tick_params(axis="y", labelsize=8, pad=2, length=3.5, width=0.75)
        ax.yaxis.set_major_locator(MultipleLocator(y_tick_step))
        ax.yaxis.set_minor_locator(MultipleLocator(y_tick_step / 2))
        ax.yaxis.grid(True, linestyle=":", linewidth=0.5, alpha=0.55, zorder=0, which="major")
        ax.set_axisbelow(True)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("0.25")
        ax.spines["bottom"].set_color("0.25")

        # Band labels: y in axes fraction; tight y_lim brings bar tops up toward this line.
        ax.text(
            w_g / 2, 0.78, "Secure",
            ha="center", va="top", fontsize=8,
            color=_COLOR_SAFE, fontweight="semibold",
            transform=x_y_text,
        )
        ax.text(
            w_g + (1.0 - w_g) / 2, 0.78, "Eve detected",
            ha="center", va="top", fontsize=8,
            color=_COLOR_DANGER, fontweight="semibold",
            transform=x_y_text,
        )

        atk_patch = mpatches.Patch(
            facecolor=_COLOR_ATTACK, edgecolor=_edge, linewidth=0.35, label=label_attack
        )
        hon_patch = mpatches.Patch(
            facecolor=_COLOR_HONEST, edgecolor=_edge, linewidth=0.35, label=label_honest
        )
        thr_line = Line2D(
            [0], [0],
            color=_COLOR_THRESH,
            linestyle=(0, (4, 3)),
            linewidth=1.0,
            label=f"Threshold ({threshold:.0f}% error)",
        )
        leg = ax.legend(
            handles=[atk_patch, hon_patch, thr_line],
            loc="upper left",
            fontsize=7.5,
            facecolor="white",
            framealpha=0.96,
            borderpad=0.45,
            handlelength=1.35,
            handletextpad=0.45,
            labelspacing=0.3,
            borderaxespad=0.55,
        )
        leg.get_frame().set_linewidth(0.55)

        # bbox_inches="tight" handles all boundary padding; rect= is redundant.
        fig.tight_layout(pad=0.6)
        fig.savefig(output_file, format="pdf", dpi=300, bbox_inches="tight", pad_inches=0.08)
        plt.close(fig)


def plot_fig1_imr(
    err_imr,
    err_honest,
    output_file="fig1_MeasureResend_vs_EB.pdf",
    *,
    bar_w_u: float | None = None,
    y_lim_hi: int | None = None,
):
    _plot_error_fig(
        err_imr,
        err_honest,
        label_attack="Measure-Resend Attack",
        label_honest="Honest EB Protocol",
        title="Measure-Resend Attack vs. Honest EB Protocol",
        output_file=output_file,
        bar_w_u=bar_w_u,
        y_lim_hi=y_lim_hi,
        omit_x_ticks=(-5.0,),
    )


def plot_fig2_v1(
    err_v1,
    err_honest,
    output_file="fig2_V1_vs_EB.pdf",
    *,
    bar_w_u: float | None = None,
    y_lim_hi: int | None = None,
):
    _plot_error_fig(
        err_v1,
        err_honest,
        label_attack="V1: Entanglement Injection Attack",
        label_honest="Honest EB Protocol",
        title="V1 Attack (Entanglement Injection) vs. Honest EB",
        output_file=output_file,
        bar_w_u=bar_w_u,
        y_lim_hi=y_lim_hi,
    )
