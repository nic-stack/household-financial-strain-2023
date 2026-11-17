"""Weighted estimates with standard errors from the survey's 44 replicate weights.

The Consumer Expenditure Survey publishes 44 half-sample replicate weights (WTREP01-WTREP44).
An estimate is recomputed with each replicate weight, and the variance is
    var = (1/44) * sum_r (estimate_r - estimate)^2
Pooling the four quarterly files gives an average over the year; dividing a weight total by 4
gives the average number of U.S. households (consumer units).
"""
import numpy as np
import pandas as pd

REPS = [f"WTREP{i:02d}" for i in range(1, 45)]
N_FILES = 4


def share(df, flag):
    """Weighted share of households where `flag` is true, with SE and 95% interval (in %)."""
    y = df[flag].astype(float).to_numpy()
    est = np.average(y, weights=df.weight)
    reps = np.array([np.average(y, weights=df[r]) if df[r].sum() > 0 else est for r in REPS])
    se = np.sqrt(((reps - est) ** 2).mean())
    return {"pct": 100 * est, "se_pct": 100 * se, "ci_low": 100 * max(est - 1.96 * se, 0.0), "ci_high": 100 * (est + 1.96 * se),
            "households_m": df.loc[df[flag], "weight"].sum() / N_FILES / 1e6, "interviews": len(df)}


def mean(df, col):
    est = np.average(df[col], weights=df.weight)
    reps = np.array([np.average(df[col], weights=df[r]) for r in REPS])
    se = np.sqrt(((reps - est) ** 2).mean())
    return {"mean": est, "se": se, "interviews": len(df)}


def by_group(df, flag, group, order=None):
    rows = []
    for g, sub in df.groupby(group, observed=True):
        rows.append({"group_var": group, "group": g, **share(sub, flag)})
    out = pd.DataFrame(rows)
    if order is not None:
        out["group"] = pd.Categorical(out.group, order, ordered=True)
        out = out.sort_values("group")
    return out
