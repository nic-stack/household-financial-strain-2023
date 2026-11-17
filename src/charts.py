"""Step 4: charts from results/*.csv."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
R, C = ROOT / "results", ROOT / "charts"
C.mkdir(exist_ok=True)
INK, MUTED, ACCENT, SOFT, LIGHT = "#1F2933", "#7B8794", "#C2593F", "#E8B4A6", "#E4E7EB"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
                     "text.color": INK})
SRC = "Source: BLS Consumer Expenditure Survey, 2023 interview files (Apr 2023 - Mar 2024). Survey-weighted; bars show 95% intervals."


def finish(fig, title, sub, src=SRC):
    fig.text(0.01, 0.975, title, fontsize=14, weight="bold", va="top")
    fig.text(0.01, 0.925, sub, fontsize=9.5, color=MUTED, va="top", linespacing=1.4)
    fig.text(0.01, 0.012, src, fontsize=7.5, color=MUTED)


# 1. what each fix did to the original team result
r = pd.read_csv(R / "team_reconciliation.csv")
labels = ["Original\nteam result", "+ missing\nspending column", "+ 3 months vs\n3 months income",
          "+ imputed\nincome", "+ survey\nweights", "+ full year"]
fig, ax = plt.subplots(figsize=(10, 5)); fig.subplots_adjust(top=.78, bottom=.2, left=.07, right=.98)
cols = [MUTED] + [ACCENT] * 2 + [SOFT] * 3
bars = ax.bar(labels, r.pct, color=cols, width=.62)
for b, v in zip(bars, r.pct):
    ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.1f}%", ha="center", fontsize=10, weight="bold")
ax.set_ylabel("Households flagged by the team's rule (%)"); ax.set_ylim(0, max(r.pct) * 1.18)
finish(fig, "The original 3.5% came from two data errors",
       "Same rule as the team project, fixed one step at a time. With the errors fixed,\nthe rule flags about 41% of households: far too broad to mean 'vulnerable'.",
       "Source: BLS Consumer Expenditure Survey 2023. Steps 0-3 count interviews (Apr-Jun 2023); steps 4-5 are survey-weighted.")
fig.savefig(C / "01_team_reconciliation.png", dpi=160); plt.close()

# 2. who is housing-cost burdened
b = pd.read_csv(R / "by_group.csv")
b = b[b.measure == "burdened"]
blocks = [("income_quintile", "Income"), ("tenure", "Housing"), ("earners_group", "Earners"),
          ("household_type", "Household"), ("age_group", "Age")]
rows = []
for gv, name in blocks:
    sub = b[b.group_var == gv]
    rows.append(("__" + name, None, None, None))
    rows += [(g, p, lo, hi) for g, p, lo, hi in sub[["group", "pct", "ci_low", "ci_high"]].itertuples(index=False)]
overall = pd.read_csv(R / "headline.csv").set_index("measure").pct["Housing cost burden (>30% of income)"]
fig, ax = plt.subplots(figsize=(10, 9.5)); fig.subplots_adjust(top=.89, bottom=.09, left=.22, right=.97)
y = list(range(len(rows)))[::-1]
for yi, (g, p, lo, hi) in zip(y, rows):
    if p is None:
        ax.text(-1, yi, g[2:].upper(), fontsize=9, weight="bold", color=MUTED, va="center", ha="right")
        continue
    col = ACCENT if p > overall else MUTED
    ax.plot([lo, hi], [yi, yi], color=col, lw=2.2, alpha=.5)
    ax.plot(p, yi, "o", color=col, ms=7)
    ax.text(hi + 1.2, yi, f"{p:.0f}%", va="center", fontsize=9)
ax.axvline(overall, color=INK, lw=.8, ls="--")
ax.text(overall + .5, -0.9, f"All households {overall:.0f}%", fontsize=8.5)
ax.set_ylim(-1.5, len(rows) - .3)
ax.set_yticks([yi for yi, r_ in zip(y, rows) if r_[1] is not None])
ax.set_yticklabels([r_[0] for r_ in rows if r_[1] is not None])
ax.set_xlim(0, 70); ax.set_xlabel("Households spending more than 30% of before-tax income on housing (%)")
finish(fig, "Housing strain is concentrated among renters, people living alone and low-income households",
       "Share of U.S. households with a housing cost burden, 2023. Orange = above the national rate.")
fig.savefig(C / "02_burden_by_group.png", dpi=160); plt.close()

# 3. where the money goes
s = pd.read_csv(R / "spending_profile.csv").set_index("group")
parts = [c for c in s.columns if c.startswith("share_")]
names = {"share_housing (rent/owner costs + utilities)": "Housing", "share_food": "Food",
         "share_transportation": "Transport", "share_healthcare": "Healthcare"}
palette = [ACCENT, SOFT, MUTED, LIGHT]
order = ["Severely burdened renters", "Other renters", "Severely burdened owners", "Other owners"]
fig, ax = plt.subplots(figsize=(10, 4.8)); fig.subplots_adjust(top=.76, bottom=.16, left=.24, right=.97)
left = pd.Series(0.0, index=order)
for c, col in zip(parts, palette):
    v = s.loc[order, c]
    ax.barh(order[::-1], v[::-1], left=left[::-1], color=col, label=names[c], height=.6)
    for i, g in enumerate(order[::-1]):
        if v[g] >= 4:
            ax.text(left[g] + v[g] / 2, i, f"{v[g]:.0f}%", ha="center", va="center", fontsize=8.5,
                    color="white" if col in (ACCENT, MUTED) else INK)
    left += v
for i, g in enumerate(order[::-1]):
    ax.text(left[g] + 1, i, f"median income ${s.loc[g, 'median_income_before_tax'] / 1000:.0f}k", va="center", fontsize=8.5, color=MUTED)
ax.set_xlim(0, 100); ax.set_xlabel("Share of total spending (%)")
ax.legend(frameon=False, ncol=4, fontsize=8.5, loc="upper left", bbox_to_anchor=(0, 1.1))
finish(fig, "Severely burdened renters put 44% of their spending into housing",
       "Spending shares for households paying more than 50% of income on housing, compared with everyone else.",
       "Source: BLS Consumer Expenditure Survey, 2023 interview files. Survey-weighted. Owner totals include mortgage principal.")
fig.savefig(C / "03_spending_profile.png", dpi=160); plt.close()
print("charts written")
