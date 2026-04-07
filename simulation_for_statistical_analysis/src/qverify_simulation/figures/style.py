FIG_WIDTH_IN_SINGLE_COL = 3.5
FIG_HEIGHT_BAR_SINGLE = 3.3
# 3.5 in height matches the 3.5 in width; tighter than the old 3.85 in.
FIG_HEIGHT_REL_ERR = 3.5

PAPER_RC = {
    "font.family": "serif",
    "font.size": 9,
    "axes.labelsize": 10,
    "axes.titlesize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "axes.linewidth": 0.85,
    "xtick.major.width": 0.75,
    "ytick.major.width": 0.75,
    "xtick.minor.width": 0.45,
    "ytick.minor.width": 0.45,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "legend.frameon": True,      # was False; all figures use an explicit frame, keep RC consistent
    "legend.fancybox": False,
    "legend.edgecolor": "0.82",
}

# Colorblind-safe pair (Wong/IBM palette): vermillion + blue.
# Separates well in grayscale and under deuteranopia/protanopia.
# _COLOR_HONEST was #d6604d (red-orange) — too close to _COLOR_THRESH in grayscale.
# _COLOR_DANGER was #d01c8b (magenta) — garish in print; muted red is calmer.
_COLOR_ATTACK = "#D55E00"   # CB-safe vermillion (was blue #0072B2)
_COLOR_HONEST = "#0072B2"   # CB-safe blue (was amber #E69F00)
_COLOR_SAFE   = "#4dac26"
_COLOR_DANGER = "#CC3311"   # muted red     (was #d01c8b)
_COLOR_THRESH = "#b2182b"
