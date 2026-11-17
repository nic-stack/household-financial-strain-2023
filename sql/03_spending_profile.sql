-- Step 3: where the money goes for severely burdened households compared with everyone else.
-- BLS total spending excludes mortgage principal (it counts as paying down debt), but the housing
-- cost measure includes it, so principal is added to the total to keep the shares like for like.

CREATE OR REPLACE TABLE spending_profile AS
WITH labelled AS (
    SELECT *,
           CASE WHEN tenure = 'Renter' THEN 'renters' ELSE 'owners' END AS tenure2,
           CASE WHEN tenure = 'Renter' AND severely_burdened THEN 'Severely burdened renters'
                WHEN tenure = 'Renter'                       THEN 'Other renters'
                WHEN severely_burdened                       THEN 'Severely burdened owners'
                ELSE 'Other owners' END AS profile_group,
           spend_total + mortgage_principal AS spend_incl_principal
    FROM measured
    WHERE housed
),
-- weighted median income: the first income where the running weight passes half the group's weight
running AS (
    SELECT profile_group, income_before_tax,
           SUM(weight) OVER (PARTITION BY profile_group ORDER BY income_before_tax
                             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_w,
           SUM(weight) OVER (PARTITION BY profile_group)                        AS total_w
    FROM labelled
),
medians AS (
    SELECT profile_group, MIN(income_before_tax) AS median_income
    FROM running
    WHERE cum_w >= total_w / 2
    GROUP BY profile_group
)
SELECT l.profile_group AS "group",
       COUNT(*)                                                                   AS interviews,
       ROUND(m.median_income, -2)                                                 AS median_income_before_tax,
       ROUND(4 * SUM(weight * spend_incl_principal) / SUM(weight), -1)            AS mean_annual_spending_incl_principal,
       ROUND(100 * SUM(weight * housing_cost)    / SUM(weight * spend_incl_principal), 1) AS share_housing,
       ROUND(100 * SUM(weight * spend_food)      / SUM(weight * spend_incl_principal), 1) AS share_food,
       ROUND(100 * SUM(weight * spend_transport) / SUM(weight * spend_incl_principal), 1) AS share_transportation,
       ROUND(100 * SUM(weight * spend_health)    / SUM(weight * spend_incl_principal), 1) AS share_healthcare
FROM labelled l
JOIN medians m USING (profile_group)
GROUP BY l.profile_group, m.median_income
ORDER BY CASE l.profile_group WHEN 'Severely burdened renters' THEN 1 WHEN 'Other renters' THEN 2
                              WHEN 'Severely burdened owners' THEN 3 ELSE 4 END;
