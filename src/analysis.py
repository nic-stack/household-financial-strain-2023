"""Step 3: who is financially stretched? Standard definitions, survey-weighted, with 95% intervals.

Measures (each household interview covers 3 months of spending; income is annual, so it is divided by 4):
  * Housing cost burden (HUD standard): housing costs > 30% of before-tax income.
    Severe burden: > 50%. Renters and owners only.
  * Spending more than income: 3-month spending > 3 months of after-tax income.
    Also shown without vehicle purchases, because buying a car makes one quarter look unusually high.
    This turned out NOT to be a good vulnerability measure (see README): it mostly flags retirees
    spending savings, and low-income households, whose income this survey is known to under-record.
    It is kept as a tested-and-rejected measure.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from estimate import share, mean, by_group

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
t = pd.read_csv(ROOT / "data" / "processed" / "interviews.csv", low_memory=False)

inc_q = t.income_before_tax / 4
inc_after_q = t.income_after_tax / 4
housed = t.tenure.isin(["Renter", "Owner with mortgage", "Owner, no mortgage"]) & (inc_q > 0)
t["burden_ratio"] = np.where(housed, t.housing_cost / inc_q, np.nan)
t["burdened"] = t.burden_ratio > .30
t["severely_burdened"] = t.burden_ratio > .50
t["overspend"] = t.spend_total > inc_after_q
t["overspend_ex_vehicle"] = (t.spend_total - t.spend_vehicle_purchase) > inc_after_q

H = t[housed].copy()

# ---------------------------------------------------------------- 1. headline numbers
head = pd.DataFrame([
    {"measure": "Housing cost burden (>30% of income)", **share(H, "burdened")},
    {"measure": "Severe housing cost burden (>50% of income)", **share(H, "severely_burdened")},
    {"measure": "Renters: housing cost burden", **share(H[H.tenure == "Renter"], "burdened")},
    {"measure": "Renters: severe burden", **share(H[H.tenure == "Renter"], "severely_burdened")},
    {"measure": "Owners: housing cost burden", **share(H[H.tenure != "Renter"], "burdened")},
    {"measure": "Owners: housing cost burden incl. repairs + insurance (upper bound)",
     **share(H[H.tenure != "Renter"].assign(_f=lambda x: (x.housing_cost + x.owner_repairs_insurance) / (x.income_before_tax / 4) > .30), "_f")},
    {"measure": "Spent more than after-tax income (3 months)", **share(t, "overspend")},
    {"measure": "Spent more than after-tax income, excluding vehicle purchases", **share(t, "overspend_ex_vehicle")},
])
head.round(2).to_csv(RES / "headline.csv", index=False)

# ---------------------------------------------------------------- 2. by group
orders = {
    "income_quintile": ["Lowest 20%", "Second 20%", "Middle 20%", "Fourth 20%", "Highest 20%"],
    "age_group": ["Under 35", "35-44", "45-54", "55-64", "65-74", "75+"],
    "tenure": ["Renter", "Owner with mortgage", "Owner, no mortgage"],
    "region": ["Northeast", "Midwest", "South", "West"],
    "earners_group": ["No earners", "One earner", "Two or more"],
    "household_type": ["Living alone", "Adults only", "With children"],
}
groups = []
for flag in ["burdened", "severely_burdened"]:
    for g, order in orders.items():
        groups.append(by_group(H, flag, g, order).assign(measure=flag))
for g, order in orders.items():
    groups.append(by_group(t[t.tenure != "Other (no cash rent / student)"] if g == "tenure" else t,
                           "overspend_ex_vehicle", g, order).assign(measure="overspend_ex_vehicle"))
by = pd.concat(groups, ignore_index=True).dropna(subset=["group"])   # drops "region not stated" (suppressed by BLS)
by = by[["measure", "group_var", "group", "pct", "se_pct", "ci_low", "ci_high", "households_m", "interviews"]]
by.round(2).to_csv(RES / "by_group.csv", index=False)

# ---------------------------------------------------------------- 3. where the money goes
def weighted_median(x, w):
    o = np.argsort(x.to_numpy()); x, w = x.to_numpy()[o], w.to_numpy()[o]
    return float(x[np.searchsorted(np.cumsum(w), w.sum() / 2)])


rows = []
for label, sub in [("Severely burdened renters", H[(H.tenure == "Renter") & H.severely_burdened]),
                   ("Other renters", H[(H.tenure == "Renter") & ~H.severely_burdened]),
                   ("Severely burdened owners", H[(H.tenure != "Renter") & H.severely_burdened]),
                   ("Other owners", H[(H.tenure != "Renter") & ~H.severely_burdened])]:
    w = sub.weight
    # BLS total spending excludes mortgage principal (it counts as paying down debt), but the housing cost
    # measure includes it, so principal is added to the total to keep the shares like for like.
    tot = ((sub.spend_total + sub.mortgage_principal) * w).sum()
    r = {"group": label, "interviews": len(sub),
         "median_income_before_tax": round(weighted_median(sub.income_before_tax, w), -2),
         "mean_annual_spending_incl_principal": round(4 * np.average(sub.spend_total + sub.mortgage_principal, weights=w), -1)}
    for c, n in [("housing_cost", "housing (rent/owner costs + utilities)"), ("spend_food", "food"),
                 ("spend_transport", "transportation"), ("spend_health", "healthcare")]:
        r[f"share_{n}"] = round(100 * (sub[c] * w).sum() / tot, 1)
    rows.append(r)
pd.DataFrame(rows).to_csv(RES / "spending_profile.csv", index=False)

# ---------------------------------------------------------------- 4. sensitivity: how much do the thresholds matter?
sens = []
for thr in [.25, .30, .35, .40, .50]:
    H["_f"] = H.burden_ratio > thr
    sens.append({"threshold_pct_of_income": int(thr * 100), **{k: v for k, v in share(H, "_f").items() if k in ("pct", "ci_low", "ci_high")}})
pd.DataFrame(sens).round(2).to_csv(RES / "sensitivity_threshold.csv", index=False)

# ---------------------------------------------------------------- 5. validation against published BLS figures
# Published figures: "Consumer Expenditures in 2023", BLS news release, September 25, 2024
# https://www.bls.gov/news.release/archives/cesan_09252024.htm
# The published spending figure covers calendar 2023; these interviews cover Jan 2023 - Feb 2024,
# so a small difference is expected.
PUBLISHED = {"income_before_tax": 101805, "annual_spending": 77280, "consumer_units_m": 134.556}
val = pd.DataFrame([
    {"check": "Average income before taxes", "published_2023": PUBLISHED["income_before_tax"],
     "this_project": round(mean(t, "income_before_tax")["mean"])},
    {"check": "Average annual spending (3-month spending x 4)", "published_2023": PUBLISHED["annual_spending"],
     "this_project": round(4 * mean(t, "spend_total")["mean"])},
    {"check": "U.S. households (consumer units), millions", "published_2023": PUBLISHED["consumer_units_m"],
     "this_project": round(t.weight.sum() / 4 / 1e6, 3)},
])
val["difference_pct"] = (100 * (val.this_project / val.published_2023 - 1)).round(1)
val.to_csv(RES / "validation.csv", index=False)

# Independent benchmark: 2023 American Community Survey, as tabulated by the Congressional Research
# Service, "Housing Cost Burdens in 2023: In Brief" (R48450). Different survey, different income
# definition, so the numbers should be close but not identical.
hd = head.set_index("measure").pct
bench = pd.DataFrame([
    {"measure": "Renters with housing cost burden (%)", "acs_2023": 49.5, "this_project": round(hd["Renters: housing cost burden"], 1)},
    {"measure": "Renters with severe burden (%)", "acs_2023": 26.5, "this_project": round(hd["Renters: severe burden"], 1)},
    {"measure": "Owners with housing cost burden (%)", "acs_2023": 23.6,
     "this_project": f'{hd["Owners: housing cost burden"]:.1f} to {hd["Owners: housing cost burden incl. repairs + insurance (upper bound)"]:.1f}'},
])
bench.to_csv(RES / "benchmark_acs.csv", index=False)

pd.set_option("display.width", 200)
for f in ["headline", "validation", "benchmark_acs", "sensitivity_threshold", "spending_profile"]:
    print(f"\n== {f}\n", pd.read_csv(RES / f"{f}.csv").to_string(index=False))
print("\n== by_group\n", by.round(1).to_string(index=False))
