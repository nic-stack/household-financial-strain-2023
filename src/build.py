"""Step 1: read the four 2023 interview files and build one tidy table of household interviews.

Source: U.S. Bureau of Labor Statistics, Consumer Expenditure Survey, Interview Survey
public-use microdata, 2023 release (fmli232, fmli233, fmli234, fmli241).
Interviews run from April 2023 to March 2024 and cover spending from January 2023 to February 2024.

Every household interview reports spending for the 3 months before the interview. The survey
splits those 3 months into "this quarter" (CQ) and "last quarter" (PQ) columns depending on the
interview month, so the two must be added together to get the full 3 months.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
FILES = ["232", "233", "234", "241"]
REPS = [f"WTREP{i:02d}" for i in range(1, 45)]


def both(df, stem):
    """3-month amount: this-quarter column + last-quarter column."""
    return df[f"{stem}CQ"].fillna(0) + df[f"{stem}PQ"].fillna(0)


frames = []
for q in FILES:
    f = RAW / f"fmli{q}.csv"
    if not f.exists():
        raise SystemExit(f"Missing {f}. See data/README.md for how to download the BLS files.")
    frames.append(pd.read_csv(f, low_memory=False, dtype={"NEWID": str}).assign(file=q))
d = pd.concat(frames, ignore_index=True)

t = pd.DataFrame({
    "newid": d.NEWID.astype(str),
    "household_id": d.NEWID.astype(str).str[:-1],      # last digit of NEWID = interview number
    "file": d.file,
    "interview_month": d.QINTRVMO.astype(int),
    "interview_year": d.QINTRVYR.astype(int),
    "weight": d.FINLWT21,
    # income (last 12 months, annual). *_reported = collected only; *_imputed = BLS-imputed where missing
    "income_before_tax_reported": d.FINCBTAX,
    "income_before_tax": d.FINCBTXM,
    "income_after_tax": d.FINATXEM,
    "income_rank": d.INC_RANK,
    # 3-month spending
    "spend_total": both(d, "TOTEXP"),
    "spend_food": both(d, "FOOD"),
    "spend_housing_all": both(d, "HOUS"),     # BLS "housing": shelter, utilities, furnishings, operations
    "spend_transport": both(d, "TRANS"),
    "spend_health": both(d, "HEALTH"),
    "spend_vehicle_purchase": both(d, "CARTKN") + both(d, "CARTKU") + both(d, "OTHVEH"),
    "rent": both(d, "RNTXRP"),
    "mortgage_interest": both(d, "MRTINT"),
    "property_tax": both(d, "PROPTX"),
    "mortgage_principal": d.EMRTPNOC.fillna(0) + d.EMRTPNOP.fillna(0),   # owned home (MRTPRNO* is the vacation home)
    "utilities": both(d, "UTIL"),
    "owner_repairs_insurance": both(d, "MRPINS"),   # repairs + insurance together (used only as an upper bound)
    # the columns the original team project used (this quarter only)
    "team_totexp": d.TOTEXPCQ, "team_hous": d.HOUSCQ, "team_food": d.FOODCQ,
    "team_health": d.HEALTHCQ, "team_trans": d.TRANSCQ,
    # household characteristics
    "tenure_code": d.CUTENURE.astype(int),
    "age_ref": d.AGE_REF.astype(int),
    "region_code": pd.to_numeric(d.REGION, errors="coerce"),
    "fam_size": d.FAM_SIZE.astype(int),
    "earners": d.NO_EARNR.astype(int),
    "children": d.PERSLT18.astype(int),
})
t[REPS] = d[REPS].fillna(0)        # a blank replicate weight means "not in this half-sample"

# Housing cost in the HUD sense (rent or owner costs + utilities). Repairs are excluded; the owner
# insurance amount cannot be separated from repairs in this file, so it is left out (slight understatement).
renter = t.tenure_code == 4
owner = t.tenure_code.isin([1, 2, 3])
t["housing_cost"] = np.where(renter, t.rent + t.utilities,
                     np.where(owner, t.mortgage_interest + t.mortgage_principal + t.property_tax + t.utilities, np.nan))

t["tenure"] = np.select([t.tenure_code == 1, t.tenure_code.isin([2]), renter],
                        ["Owner with mortgage", "Owner, no mortgage", "Renter"], "Other (no cash rent / student)")
t["region"] = t.region_code.map({1: "Northeast", 2: "Midwest", 3: "South", 4: "West"}).fillna("Not stated")
t["income_quintile"] = pd.cut(t.income_rank, [-0.001, .2, .4, .6, .8, 1.0001],
                              labels=["Lowest 20%", "Second 20%", "Middle 20%", "Fourth 20%", "Highest 20%"])
t["age_group"] = pd.cut(t.age_ref, [0, 34, 44, 54, 64, 74, 200],
                        labels=["Under 35", "35-44", "45-54", "55-64", "65-74", "75+"])
t["earners_group"] = t.earners.clip(upper=2).map({0: "No earners", 1: "One earner", 2: "Two or more"})
t["household_type"] = np.where(t.children > 0, "With children", np.where(t.fam_size == 1, "Living alone", "Adults only"))

t.to_csv(OUT / "interviews.csv", index=False)

# checks written alongside the data
chk = {
    "interviews": len(t),
    "households": t.household_id.nunique(),
    "interviews with $0 3-month spending": int((t.spend_total == 0).sum()),
    "interviews with $0 spending using this-quarter column only": int((t.team_totexp == 0).sum()),
    "interviews with reported income <= 0": int((t.income_before_tax_reported <= 0).sum()),
    "interviews with imputed income <= 0": int((t.income_before_tax <= 0).sum()),
    "max gap between weight total and each replicate total (%)":
        round(float(max(abs(t.groupby("file")[r].sum() / t.groupby("file").weight.sum() - 1).max() for r in REPS) * 100), 2),
}
pd.Series(chk).to_csv(ROOT / "results" / "build_checks.csv", header=["value"])
print(pd.Series(chk).to_string())
