"""Render the Latvian cage-free egg-listings figures, in both languages.

Two figures, each produced in a Latvian and an English variant (all labels in
that one language, so the LV page shows fully Latvian charts and the EN page
fully English charts):
  1. Stacked horizontal bar per retailer (EU production-code mix), cage-free
     share annotated, dashed reference line at the national cage-free production
     share (~47%), chains without an online catalogue shown as a labelled row.
  2. Strip plot of price per egg by retailer, coloured by production system.

Output (in repo root): the Latvian variants keep the original filenames
(fig_lv_listings_mix_<tag>.png, fig_lv_price_per_egg_<tag>.png); the English
variants add an _en suffix (fig_lv_listings_mix_en_<tag>.png, ...).

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

CODE_COLOR = {0: COLOR_ORGANIC, 1: COLOR_FREE_RANGE, 2: COLOR_BARN, 3: COLOR_CAGED, None: COLOR_UNKNOWN}

NATIONAL_CF_PCT = 47           # Latvia cage-free production capacity, 2026 (Eglitis & Kanepajs 2026)

# All user-facing figure text, per language. The figures are outward-facing
# under Art's name, so no em dashes here (the middle dot separates title parts).
STR = {
    "lv": {
        "mix_title":    "Bezsprostu olu īpatsvars Latvijas veikalos",
        "mix_xlabel":   "Vistu (čaumalas) olu pozīciju īpatsvars (%)",
        "no_catalogue": "nav tiešsaistes olu kataloga",
        "ref_line":     "valsts ražošana\n~{n}% bezsprostu",
        "cf":           "  bezsprostu {strict}%",
        "cf_anchor":    "  bezsprostu {strict}% (korekcija {anchor}%)",
        "price_title":  "Olu cena pa tirgotājiem un turēšanas veidu",
        "price_ylabel": "Cena par olu (EUR)",
        "price_median": "mediāna {med:.2f}",
        "no_price":     "Nav cenu datu",
        "codes":        {0: "0 bioloģiskās", 1: "1 brīvās turēšanas", 2: "2 kūtī dētas",
                         3: "3 sprostos", None: "nezināms"},
    },
    "en": {
        "mix_title":    "Cage-free share of egg listings at Latvian retailers",
        "mix_xlabel":   "Share of chicken shell-egg listings (%)",
        "no_catalogue": "no online egg catalogue",
        "ref_line":     "national production\n~{n}% cage-free",
        "cf":           "  cage-free {strict}%",
        "cf_anchor":    "  cage-free {strict}% (anchor {anchor}%)",
        "price_title":  "Egg price by retailer and production system",
        "price_ylabel": "Price per egg (EUR)",
        "price_median": "median {med:.2f}",
        "no_price":     "No price data",
        "codes":        {0: "0 organic", 1: "1 free-range", 2: "2 barn",
                         3: "3 caged", None: "unknown"},
    },
}


def default_tag() -> str:
    d = date.today()
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}-LV"


def make_figure(summary_rows: list[dict], out: Path, tag: str, lang: str) -> None:
    s = STR[lang]
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
            ax.text(50, yi, s["no_catalogue"], ha="center", va="center",
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
        label = s["cf"].format(strict=strict)
        if anchor != strict:
            label = s["cf_anchor"].format(strict=strict, anchor=anchor)
        ax.text(101, yi, label, ha="left", va="center", fontsize=8.5, fontweight="bold", color="#36453e")

    # National production reference line.
    ax.axvline(NATIONAL_CF_PCT, color="#744c5b", linestyle="--", linewidth=1.2, zorder=5)
    ax.text(NATIONAL_CF_PCT, -0.85, s["ref_line"].format(n=NATIONAL_CF_PCT),
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
    ax.set_xlabel(s["mix_xlabel"])
    ax.set_title(s["mix_title"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", alpha=0.25, linestyle=":")
    ax.set_axisbelow(True)

    legend_items = [
        mpatches.Patch(facecolor=COLOR_ORGANIC,    label=s["codes"][0]),
        mpatches.Patch(facecolor=COLOR_FREE_RANGE, label=s["codes"][1]),
        mpatches.Patch(facecolor=COLOR_BARN,       label=s["codes"][2]),
        mpatches.Patch(facecolor=COLOR_CAGED,      label=s["codes"][3]),
    ]
    if any((r.get("unknown") or 0) > 0 for r in rows):
        legend_items.append(mpatches.Patch(facecolor=COLOR_UNKNOWN, label=s["codes"][None]))
    ax.legend(handles=legend_items, loc="lower center", bbox_to_anchor=(0.5, -0.30 - 0.02 * n),
              ncol=len(legend_items), frameon=False, fontsize=8.5, handlelength=1.2, handleheight=1.0)

    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight", dpi=300)
    plt.close(fig)


def make_price_figure(raw_rows: list[dict], out: Path, tag: str, lang: str) -> None:
    """Strip plot: x = retailer, y = price per egg (EUR), one point per product,
    colored by EU production system. A short grey dash marks each retailer's median.
    """
    s = STR[lang]
    # Same set the scraper takes the median over: every shell egg with a parseable
    # per-egg price (regardless of production code), so the chart median equals the
    # table's median_price_per_egg even if an unlabelled egg ever appears.
    pts = [r for r in raw_rows
           if r.get("is_shell_egg") and r.get("price_per_egg") is not None]
    if not pts:
        fig, ax = plt.subplots(figsize=(7.6, 4.8), dpi=300)
        ax.text(0.5, 0.5, s["no_price"], ha="center", va="center",
                transform=ax.transAxes, color="#999999")
        ax.set_axis_off()
        fig.savefig(out, bbox_inches="tight", dpi=300)
        plt.close(fig)
        return

    # Retailers present, ordered by basket size (desc) for consistency with the mix figure.
    counts: dict[str, int] = {}
    for r in pts:
        counts[r["retailer"]] = counts.get(r["retailer"], 0) + 1
    shops = sorted(counts, key=lambda x: counts[x], reverse=True)
    xpos = {sh: i for i, sh in enumerate(shops)}

    fig, ax = plt.subplots(figsize=(7.6, 4.8), dpi=300)

    for sh in shops:
        col = [r for r in pts if r["retailer"] == sh]
        # Deterministic horizontal jitter (no RNG, uncorrelated with price): a
        # golden-ratio sequence spreads points evenly across a +/-0.18 band so the
        # x-offset carries no meaning beyond separating overlapping dots.
        for i, r in enumerate(col):
            offset = ((i * 0.6180339887) % 1.0 - 0.5) * 0.36
            ax.scatter(xpos[sh] + offset, r["price_per_egg"],
                       s=80, color=CODE_COLOR.get(r["eu_code"], COLOR_UNKNOWN), edgecolor="white", linewidth=0.7,
                       alpha=0.9, zorder=3)
        # Median dash.
        ys = sorted(r["price_per_egg"] for r in col)
        med = ys[len(ys) // 2] if len(ys) % 2 else (ys[len(ys) // 2 - 1] + ys[len(ys) // 2]) / 2
        ax.plot([xpos[sh] - 0.28, xpos[sh] + 0.28], [med, med], color="#333333", linewidth=1.6, zorder=4)
        ax.text(xpos[sh] + 0.30, med, s["price_median"].format(med=med), va="center", ha="left",
                fontsize=7.5, color="#333333")

    ax.set_xticks(range(len(shops)))
    ax.set_xticklabels([f"{sh}\n(n={counts[sh]})" for sh in shops])
    ax.set_xlim(-0.6, len(shops) - 0.4 + 0.6)
    ax.set_ylim(0, max((r["price_per_egg"] for r in pts), default=1.0) * 1.12)
    ax.set_ylabel(s["price_ylabel"])
    ax.set_title(s["price_title"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.25, linestyle=":")
    ax.set_axisbelow(True)

    present = {r["eu_code"] for r in pts}
    legend_items = [mpatches.Patch(facecolor=CODE_COLOR[c], label=s["codes"][c])
                    for c in [0, 1, 2, 3, None] if c in present]
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

    # Latvian variants keep the original filenames; English variants add _en.
    outputs = {
        "lv": (root / f"fig_lv_listings_mix_{tag}.png", root / f"fig_lv_price_per_egg_{tag}.png"),
        "en": (root / f"fig_lv_listings_mix_en_{tag}.png", root / f"fig_lv_price_per_egg_en_{tag}.png"),
    }
    for lang, (out_mix, out_price) in outputs.items():
        make_figure(summary_rows, out_mix, tag, lang)
        make_price_figure(raw_rows, out_price, tag, lang)
        print(f"Wrote {out_mix}")
        print(f"Wrote {out_price}")


if __name__ == "__main__":
    main()
