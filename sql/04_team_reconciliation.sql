-- Step 4: reproduce the original team result, then apply each fix one at a time.
-- Team rule: flagged if total/income > 0.95 OR housing/income > 0.50
--            OR (housing + food + health + transport)/income > 0.80
-- The team's thresholds are used here ONLY to show what each fix changes.

CREATE OR REPLACE TABLE team_reconciliation AS
WITH q2 AS (SELECT * FROM interviews WHERE file = 232),
steps AS (
    -- 0. original: this-quarter columns only, annual reported income, unweighted, Apr-Jun 2023
    SELECT 0 AS step, 'Original team method' AS change, 1.0 AS weight,
           (team_totexp / income_before_tax_reported > .95
            OR team_hous / income_before_tax_reported > .50
            OR (team_hous + team_food + team_health + team_trans) / income_before_tax_reported > .80) AS flag
    FROM q2 WHERE income_before_tax_reported > 0
    UNION ALL
    -- 1. add the last-quarter columns
    SELECT 1, 'Add the last-quarter spending columns', 1.0,
           (spend_total / income_before_tax_reported > .95
            OR spend_housing_all / income_before_tax_reported > .50
            OR (spend_housing_all + spend_food + spend_health + spend_transport) / income_before_tax_reported > .80)
    FROM q2 WHERE income_before_tax_reported > 0
    UNION ALL
    -- 2. 3 months of spending vs 3 months of income
    SELECT 2, 'Compare 3 months of spending with 3 months of income', 1.0,
           (4 * spend_total / income_before_tax_reported > .95
            OR 4 * spend_housing_all / income_before_tax_reported > .50
            OR 4 * (spend_housing_all + spend_food + spend_health + spend_transport) / income_before_tax_reported > .80)
    FROM q2 WHERE income_before_tax_reported > 0
    UNION ALL
    -- 3. imputed income keeps households that did not report income
    SELECT 3, 'Use imputed income', 1.0,
           (4 * spend_total / income_before_tax > .95
            OR 4 * spend_housing_all / income_before_tax > .50
            OR 4 * (spend_housing_all + spend_food + spend_health + spend_transport) / income_before_tax > .80)
    FROM q2 WHERE income_before_tax > 0
    UNION ALL
    -- 4. survey weights
    SELECT 4, 'Apply survey weights', weight,
           (4 * spend_total / income_before_tax > .95
            OR 4 * spend_housing_all / income_before_tax > .50
            OR 4 * (spend_housing_all + spend_food + spend_health + spend_transport) / income_before_tax > .80)
    FROM q2 WHERE income_before_tax > 0
    UNION ALL
    -- 5. full year
    SELECT 5, 'Use all four 2023 interview files', weight,
           (4 * spend_total / income_before_tax > .95
            OR 4 * spend_housing_all / income_before_tax > .50
            OR 4 * (spend_housing_all + spend_food + spend_health + spend_transport) / income_before_tax > .80)
    FROM interviews WHERE income_before_tax > 0
)
SELECT step, change,
       COUNT(*) FILTER (WHERE flag) AS flagged_interviews,
       COUNT(*)                     AS interviews,
       ROUND(100 * SUM(weight * flag::INT) / SUM(weight), 2) AS pct
FROM steps
GROUP BY step, change
ORDER BY step;
