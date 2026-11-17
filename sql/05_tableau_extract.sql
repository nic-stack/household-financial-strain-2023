-- Step 5: tables for the Tableau Public dashboard (exported to tableau/ by src/run_sql.py).

-- 1. One row per renter/owner interview. Flags are 0/1 so Tableau can compute weighted rates:
--    rate = SUM([Weight] * [Burdened]) / SUM([Weight]);  households = SUM([Weight] * flag) / 4
CREATE OR REPLACE TABLE tableau_households AS
SELECT
    newid                                             AS "Interview ID",
    weight                                            AS "Weight",
    CASE WHEN tenure = 'Renter' THEN 'Renter' ELSE 'Owner' END AS "Renter or Owner",
    tenure                                            AS "Housing",
    CAST(income_quintile AS VARCHAR)                  AS "Income Group",
    CAST(age_group AS VARCHAR)                        AS "Age Group",
    region                                            AS "Region",
    earners_group                                     AS "Earners",
    household_type                                    AS "Household Type",
    ROUND(income_before_tax, 0)                       AS "Income Before Tax (Annual)",
    ROUND(4 * housing_cost, 0)                        AS "Housing Cost (Annualized)",
    burden_ratio                                      AS "Housing Cost Share of Income",   -- unrounded: rounding can flip households sitting on a threshold
    burdened::INT                                     AS "Burdened (>30%)",
    severely_burdened::INT                            AS "Severely Burdened (>50%)",
    ROUND(4 * (spend_total + mortgage_principal), 0)  AS "Spending incl. Principal (Annualized)",
    ROUND(4 * housing_cost, 0)                        AS "Spend: Housing",
    ROUND(4 * spend_food, 0)                          AS "Spend: Food",
    ROUND(4 * spend_transport, 0)                     AS "Spend: Transport",
    ROUND(4 * spend_health, 0)                        AS "Spend: Healthcare"
FROM measured
WHERE housed
ORDER BY newid;

-- 2. Precomputed estimates with 95% intervals (Tableau cannot compute replicate-weight errors).
CREATE OR REPLACE TABLE tableau_estimates AS
SELECT
    CASE measure WHEN 'burdened' THEN 'Burdened (>30% of income)'
                 WHEN 'severely_burdened' THEN 'Severely burdened (>50%)' END AS "Measure",
    CASE group_var WHEN 'all' THEN 'All households' WHEN 'renter_or_owner' THEN 'Renter or owner'
                   WHEN 'income_quintile' THEN 'Income' WHEN 'age_group' THEN 'Age'
                   WHEN 'tenure' THEN 'Housing' WHEN 'region' THEN 'Region'
                   WHEN 'earners_group' THEN 'Earners' WHEN 'household_type' THEN 'Household type' END AS "Breakdown",
    "group"                AS "Group",
    -- sort order inside each breakdown, so Tableau shows groups in a sensible order
    CASE "group" WHEN 'Lowest 20%' THEN 1 WHEN 'Second 20%' THEN 2 WHEN 'Middle 20%' THEN 3
                 WHEN 'Fourth 20%' THEN 4 WHEN 'Highest 20%' THEN 5
                 WHEN 'Under 35' THEN 1 WHEN '35-44' THEN 2 WHEN '45-54' THEN 3 WHEN '55-64' THEN 4
                 WHEN '65-74' THEN 5 WHEN '75+' THEN 6
                 WHEN 'Renter' THEN 1 WHEN 'Owner with mortgage' THEN 2 WHEN 'Owner, no mortgage' THEN 3
                 WHEN 'No earners' THEN 1 WHEN 'One earner' THEN 2 WHEN 'Two or more' THEN 3
                 WHEN 'Living alone' THEN 1 WHEN 'Adults only' THEN 2 WHEN 'With children' THEN 3
                 ELSE 1 END AS "Sort",
    ROUND(pct / 100, 4)    AS "Rate",
    ROUND(ci_low / 100, 4) AS "Rate 95% Low",
    ROUND(ci_high / 100, 4) AS "Rate 95% High",
    households_m           AS "Households (Millions)",
    interviews             AS "Interviews"
FROM estimates
WHERE measure IN ('burdened', 'severely_burdened');

-- 3. The reconciliation of the original team result
CREATE OR REPLACE TABLE tableau_reconciliation AS
SELECT step AS "Step", change AS "Change", ROUND(pct / 100, 4) AS "Share Flagged" FROM team_reconciliation;
