"""Render the Latvian cage-free egg-listings figure.

One stacked horizontal bar per retailer (EU production-code mix), with the
cage-free share annotated, a dashed reference line at the national cage-free
production share (~47%), and chains without an online catalogue shown as a
labelled "no online egg catalogue" row.

Run from project root:
    python scripts/make_figures_lv.py 2026-Q2-LV
or simply:
    python scripts/make_figures_lv.py     # defaults to current quarter + -LV
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Colorblind-friendly palette (Okabe-Ito-derived), matching the Spain figure.
COLOR_ORGANIC    = "#117733"   # dark green
COLOR_FREE_RANGE = "#44AA99"   # teal
COLOR_BARN       = "#88CCEE"   # pale blue (still cage-free)
COLOR_CAGED      = "#CC6677"   # muted red
COLOR_UNKNOWN    = "#BBBBBB"   # neutral grey

NATIONAL_CF_PCT = 47           # Latvia cage-free production capacity, 2026 (Eglitis & Kanepajs 2026)


def default_tag() -> str:
    d = date.today()
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}-LV"


def make_figure(summary_rows: list[dict], out: Path, tag: str) -> None:
    quarter = tag.replace("-LV", "")
    with_listings = [r for r in summary_rows if (r.get("shell_egg_listings") or 0) > 0]
    without = [r for r in summary_rows if (r.get("shell_egg_listings") or 0) == 0]

    # Order chains with listings by basket size (desc).
    with_listings.sort(key=lambda r: r["shell_egg_listings"], reverse=True)

    # y-rows top to bottom: listing chains, then the no-catalogue chains.
    rows = with_listings + without
    n = len(rows)
    fig, ax = plt.subplots(figsize=(9.2, 0.62 * n + 2.0), dpi=300)

    y = list(range(n))

    def pct(r, k):
        d = r["shell_egg_listings"]
        return 100.0 * r.get(k, 0) / d if d else 0.0

    for yi, r in zip(y, rows):
        if (r.get("shell_egg_listings") or 0) == 0:
            # No online catalogue: light grey full-width hatch + label.
            ax.barh(yi, 100, color="#f2f2f0", edgecolor="#dddddd", linewidth=0.6)
            ax.text(50, yi, "no online egg catalogue", ha="center", va="center",
                    fontsize=8.5, color="#999999", style="italic")
            continue
        segs = [
            (pct(r, "organic"),    COLOR_ORGANIC),
            (pct(r, "free_range"), COLOR_FREE_RANGE),
            (pct(r, "barn"),       COLOR_BARN),
            (pct(r, "caged"),      COLOR_CAGED),
            (pct(r, "unknown"),    COLOR_UNKNOWN),
        ]
        left = 0.0
        for val, color in segs:
            if val <= 0:
                continue
            ax.barh(yi, val, left=left, color=color, edgecolor="white", linewidth=0.6)
            if val >= 7:
                dark = color in (COLOR_ORGANIC, COLOR_FREE_RANGE, COLOR_CAGED)
                ax.text(left + val / 2, yi, f"{int(round(val))}", ha="center", va="center",
                        fontsize=8, color="white" if dark else "black")
            left += val
        # Cage-free % annotation at the right margin.
        strict = r["cage_free_share_strict_pct"]
        anchor = r["cage_free_share_anchor_pct"]
        label = f"  cage-free {strict}%"
        if anchor != strict:
            label = f"  cage-free {strict}% (anchor {anchor}%)"
        ax.text(101, yi, label, ha="left", va="center", fontsize=8.5, fontweight="bold", color="#36453e")

    # National production reference line.
    ax.axvline(NATIONAL_CF_PCT, color="#744c5b", linestyle="--", linewidth=1.2, zorder=5)
    ax.text(NATIONAL_CF_PCT, -0.85, f"national production\n~{NATIONAL_CF_PCT}% cage-free",
            ha="center", va="top", fontsize=7.5, color="#744c5b")

    ax.set_yticks(y)
    labels = []
    for r in rows:
        if (r.get("shell_egg_listings") or 0) > 0:
            labels.append(f"{r['retailer']}  (n={r['shell_egg_listings']})")
        else:
            labels.append(r["retailer"])
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_ylim(n - 0.5, -1.4)
    ax.set_xlabel("Share of chicken shell-egg listings (%)")
    ax.set_title(f"Cage-free share of egg listings at Latvian retailers  ·  {quarter}")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", alpha=0.25, linestyle=":")
    ax.set_axisbelow(True)

    legend_items = [
        mpatches.Patch(facecolor=COLOR_ORGANIC,    label="0 organic"),
        mpatches.Patch(facecolor=COLOR_FREE_RANGE, label="1 free-range"),
        mpatches.Patch(facecolor=COLOR_BARN,       label="2 barn"),
        mpatches.Patch(facecolor=COLOR_CAGED,      label="3 caged"),
        mpatches.Patch(facecolor=COLOR_UNKNOWN,    label="unknown"),
    ]
    ax.legend(handles=legend_items, loc="lower center", bbox_to_anchor=(0.5, -0.30 - 0.02 * n),
              ncol=5, frameon=False, fontsize=8.5, handlelength=1.2, handleheight=1.0)

    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight", dpi=300)
    plt.close(fig)


CODE_COLOR = {0: COLOR_ORGANIC, 1: COLOR_FREE_RANGE, 2: COLOR_BARN, 3: COLOR_CAGED}
CODE_LABEL = {0: "0 organic", 1: "1 free-range", 2: "2 barn", 3: "3 caged"}


def make_price_figure(raw_rows: list[dict], out: Path, tag: str) -> None:
    """Strip plot: x = retailer, y = price per egg (EUR), one point per product,
    colored by EU production system. A short grey dash marks each retailer's median.
    """
    quarter = tag.replace("-LV", "")
    pts = [r for r in raw_rows
           if r.get("is_shell_egg") and r.get("price_per_egg") is not None and r.get("eu_code") is not None]

    # Retailers present, ordered by basket size (desc) for consistency with the mix figure.
    counts: dict[str, int] = {}
    for r in pts:
        counts[r["retailer"]] = counts.get(r["retailer"], 0) + 1
    shops = sorted(counts, key=lambda s: counts[s], reverse=True)
    xpos = {s: i for i, s in enumerate(shops)}

    fig, ax = plt.subplots(figsize=(7.6, 4.8), dpi=300)

    for s in shops:
        col = [r for r in pts if r["retailer"] == s]
        # Deterministic horizontal jitter (no RNG, uncorrelated with price): a
        # golden-ratio sequence spreads points evenly across a +/-0.18 band so the
        # x-offset carries no meaning beyond separating overlapping dots.
        for i, r in enumerate(col):
            offset = ((i * 0.6180339887) % 1.0 - 0.5) * 0.36
            ax.scatter(xpos[s] + offset, r["price_per_egg"],
                       s=80, color=CODE_COLOR[r["eu_code"]], edgecolor="white", linewidth=0.7,
                       alpha=0.9, zorder=3)
        # Median dash.
        ys = sorted(r["price_per_egg"] for r in col)
        med = ys[len(ys) // 2] if len(ys) % 2 else (ys[len(ys) // 2 - 1] + ys[len(ys) // 2]) / 2
        ax.plot([xpos[s] - 0.28, xpos[s] + 0.28], [med, med], color="#333333", linewidth=1.6, zorder=4)
        ax.text(xpos[s] + 0.30, med, f"mediāna {med:.2f}", va="center", ha="left", fontsize=7.5, color="#333333")

    ax.set_xticks(range(len(shops)))
    ax.set_xticklabels([f"{s}\n(n={counts[s]})" for s in shops])
    ax.set_xlim(-0.6, len(shops) - 0.4 + 0.6)
    ax.set_ylim(0, max(r["price_per_egg"] for r in pts) * 1.12)
    ax.set_ylabel("Cena par olu (EUR) / Price per egg (EUR)")
    ax.set_title(f"Olu cena pa tirgotājiem un turēšanas veida  ·  {quarter}")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.25, linestyle=":")
    ax.set_axisbelow(True)

    codes_present = sorted({r["eu_code"] for r in pts})
    legend_items = [mpatches.Patch(facecolor=CODE_COLOR[c], label=CODE_LABEL[c]) for c in codes_present]
    ax.legend(handles=legend_items, loc="upper center", bbox_to_anchor=(0.5, -0.13),
              ncol=len(legend_items), frameon=False, fontsize=8.5, handlelength=1.2, handleheight=1.0)

    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight", dpi=300)
    plt.close(fig)


def main() -> None:
    tag = sys.argv[1] if len(sys.argv) > 1 else default_tag()
    root = Path(__file__).resolve().parent.parent
    summary_path = root / "scraper" / "data" / "summary" / f"{tag}_summary.json"
    summary_rows = json.loads(summary_path.read_text(encoding="utf-8"))
    raw_path = root / "scraper" / "data" / "raw" / f"{tag}_listings.json"
    raw_rows = json.loads(raw_path.read_text(encoding="utf-8"))

    out_mix = root / f"fig_lv_listings_mix_{tag}.png"
    out_price = root / f"fig_lv_price_per_egg_{tag}.png"
    make_figure(summary_rows, out_mix, tag)
    make_price_figure(raw_rows, out_price, tag)
    print(f"Wrote {out_mix}")
    print(f"Wrote {out_price}")


if __name__ == "__main__":
    main()
