"""Run the SQL pipeline in DuckDB, export the results, and check them against the independent pandas version.

SQL is the main engine: results/estimates.csv, results/spending_profile.csv and
results/team_reconciliation.csv come from the SQL in sql/. The pandas scripts (analysis.py,
reconcile_team.py) compute the same numbers separately into results/pandas_check/, and every
overlapping number must agree.
"""
from pathlib import Path
import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES, CHK = ROOT / "results", ROOT / "results" / "pandas_check"
DB = ROOT / "household.duckdb"
DB.unlink(missing_ok=True)

con = duckdb.connect(str(DB))
con.execute(f"SET file_search_path = '{ROOT}'")
for f in sorted((ROOT / "sql").glob("*.sql")):
    con.execute(f.read_text())

for table in ["estimates", "spending_profile", "team_reconciliation", "sql_checks"]:
    con.table(table).df().to_csv(RES / f"{table}.csv", index=False)
TAB = ROOT / "tableau"
TAB.mkdir(exist_ok=True)
for table, name in [("tableau_households", "households_2023"), ("tableau_estimates", "estimates_with_ci"),
                    ("tableau_reconciliation", "team_reconciliation")]:
    con.table(table).df().to_csv(TAB / f"{name}.csv", index=False)
con.close()

# The Tableau extract must reproduce the SQL estimates with the formula the dashboard will use:
# SUM([Weight] * [Burdened (>30%)]) / SUM([Weight])
hh = pd.read_csv(TAB / "households_2023.csv")
est0 = pd.read_csv(RES / "estimates.csv").set_index(["measure", "group_var", "group"]).pct
rate = lambda d, f: round(100 * (d.Weight * d[f]).sum() / d.Weight.sum(), 2)
assert rate(hh, "Burdened (>30%)") == est0[("burdened", "all", "All households")]
assert rate(hh, "Severely Burdened (>50%)") == est0[("severely_burdened", "all", "All households")]
assert rate(hh[hh["Renter or Owner"] == "Renter"], "Burdened (>30%)") == est0[("burdened", "renter_or_owner", "Renters")]
# the dashboard's threshold slider uses the ratio, so it must agree with the flag on every row
assert ((hh["Housing Cost Share of Income"] > .30).astype(int) == hh["Burdened (>30%)"]).all()
assert ((hh["Housing Cost Share of Income"] > .50).astype(int) == hh["Severely Burdened (>50%)"]).all()

# ---------------------------------------------------------------- compare with pandas
TOL = 0.011    # both sides round to 2 decimals
sql_est = pd.read_csv(RES / "estimates.csv")
pd_by = pd.read_csv(CHK / "by_group.csv")
m = pd_by.merge(sql_est, on=["measure", "group_var", "group"], suffixes=("_pd", "_sql"), how="left")
assert m.pct_sql.notna().all(), f"groups missing in SQL: {m[m.pct_sql.isna()][['measure', 'group']].values}"
for c in ["pct", "se_pct", "ci_low", "ci_high"]:
    bad = m[(m[f"{c}_pd"] - m[f"{c}_sql"]).abs() > TOL]
    assert bad.empty, f"{c} differs:\n{bad}"
assert (m.interviews_pd == m.interviews_sql).all(), "interview counts differ"

head = pd.read_csv(CHK / "headline.csv").set_index("measure")
pick = {
    "Housing cost burden (>30% of income)": ("burdened", "all", "All households"),
    "Severe housing cost burden (>50% of income)": ("severely_burdened", "all", "All households"),
    "Renters: housing cost burden": ("burdened", "renter_or_owner", "Renters"),
    "Renters: severe burden": ("severely_burdened", "renter_or_owner", "Renters"),
    "Owners: housing cost burden": ("burdened", "renter_or_owner", "Owners"),
    "Owners: housing cost burden incl. repairs + insurance (upper bound)": ("owner_burdened_upper", "all", "All households"),
    "Spent more than after-tax income (3 months)": ("overspend", "all", "All households"),
    "Spent more than after-tax income, excluding vehicle purchases": ("overspend_ex_vehicle", "all", "All households"),
}
s = sql_est.set_index(["measure", "group_var", "group"])
for name, key in pick.items():
    for c in ["pct", "se_pct"]:
        assert abs(head.loc[name, c] - s.loc[key, c]) <= TOL, f"{name} {c}: pandas {head.loc[name, c]} vs SQL {s.loc[key, c]}"

sp_sql = pd.read_csv(RES / "spending_profile.csv").set_index("group")
sp_pd = pd.read_csv(CHK / "spending_profile.csv").set_index("group").rename(columns={
    "share_housing (rent/owner costs + utilities)": "share_housing"})
cols = ["interviews", "median_income_before_tax", "mean_annual_spending_incl_principal",
        "share_housing", "share_food", "share_transportation", "share_healthcare"]
diff = (sp_sql.loc[sp_pd.index, cols] - sp_pd[cols]).abs()
assert (diff <= 0.11).all().all(), f"spending profile differs:\n{diff}"

tr_sql = pd.read_csv(RES / "team_reconciliation.csv")
tr_pd = pd.read_csv(CHK / "team_reconciliation.csv")
assert ((tr_sql.pct - tr_pd.pct).abs() <= TOL).all(), "team reconciliation differs"
assert tr_sql.flagged_interviews[0] == 152 and tr_sql.interviews[0] == 4393, "SQL did not reproduce 152 of 4,393"

print(f"Tableau extract: {len(hh)} rows; weighted rates reproduce the SQL estimates")
print(f"SQL check: {len(m)} group estimates (share, SE, 95% interval), {len(pick)} headline figures, "
      f"the spending profile and all {len(tr_sql)} reconciliation steps match pandas")
print(pd.read_csv(RES / "sql_checks.csv").to_string(index=False))
