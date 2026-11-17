"""Step 2: reproduce the original team result, then apply each fix one at a time.

The original capstone (DAV 6150 team project) used the April-June 2023 file only and called a
household "financially vulnerable" if any of these held:
    total spending / income > 0.95
    housing / income         > 0.50
    (housing + food + health + transport) / income > 0.80
It compared this-quarter (CQ) spending with annual income, used reported income only, dropped
households with income <= 0, and did not use survey weights. It found 152 of 4,393 (3.46%).

The team's thresholds are kept here ONLY to show what each fix changes. The main analysis
(analysis.py) uses standard definitions instead.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
t = pd.read_csv(ROOT / "data" / "processed" / "interviews.csv", low_memory=False)


def flag(df, total, hous, essential, income):
    return (total / income > .95) | (hous / income > .50) | (essential / income > .80)


rows = []


def record(step, what, df, f, weighted=False):
    if weighted:
        pct = 100 * np.average(f, weights=df.weight)
        n = f"{df.loc[f, 'weight'].sum() / df.file.nunique() / 1e6:.1f}M US households"
    else:
        pct = 100 * f.mean()
        n = f"{int(f.sum())} of {len(df)} interviews"
    rows.append({"step": step, "change": what, "flagged": n, "pct": round(pct, 2)})


q2 = t[t.file == 232].copy()

# 0. the team's version
a = q2[q2.income_before_tax_reported > 0]
ess_cq = a.team_hous + a.team_food + a.team_health + a.team_trans
f0 = flag(a, a.team_totexp, a.team_hous, ess_cq, a.income_before_tax_reported)
record(0, "Original team method (Apr-Jun 2023, this-quarter spending vs annual reported income)", a, f0)
assert int(f0.sum()) == 152 and len(a) == 4393, "could not reproduce the team's 152 of 4,393"

# 1. add the last-quarter columns (April interviews had all 3 months in the PQ columns)
ess = a.spend_housing_all + a.spend_food + a.spend_health + a.spend_transport
f1 = flag(a, a.spend_total, a.spend_housing_all, ess, a.income_before_tax_reported)
record(1, "Add the last-quarter spending columns (3 full months for every household)", a, f1)

# 2. compare like with like: 3 months of spending vs 3 months of income
f2 = flag(a, a.spend_total * 4, a.spend_housing_all * 4, ess * 4, a.income_before_tax_reported)
record(2, "Compare 3 months of spending with 3 months of income (not 12)", a, f2)

# 3. use BLS-imputed income, so households that did not report income are kept
b = q2[q2.income_before_tax > 0]
essb = b.spend_housing_all + b.spend_food + b.spend_health + b.spend_transport
f3 = flag(b, b.spend_total * 4, b.spend_housing_all * 4, essb * 4, b.income_before_tax)
record(3, "Use imputed income (keeps households that did not report income)", b, f3)

# 4. survey weights: share of U.S. households, not share of the sample
record(4, "Apply survey weights (estimate for all U.S. households)", b, f3, weighted=True)

# 5. full year
c = t[t.income_before_tax > 0]
essc = c.spend_housing_all + c.spend_food + c.spend_health + c.spend_transport
f5 = flag(c, c.spend_total * 4, c.spend_housing_all * 4, essc * 4, c.income_before_tax)
record(5, "Use all four 2023 interview files (full year)", c, f5, weighted=True)

out = pd.DataFrame(rows)
out.to_csv(ROOT / "results" / "team_reconciliation.csv", index=False)
print(out.to_string(index=False))
