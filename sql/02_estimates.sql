-- Step 2: survey-weighted shares with standard errors from the 44 replicate weights.
--   share      = SUM(weight * flag) / SUM(weight)
--   replicate  = the same share using each replicate weight instead
--   SE         = SQRT( AVG over 44 replicates of (replicate share - share)^2 )
-- The four quarterly files are pooled; dividing a weight total by 4 gives average U.S. households.

-- Every (measure, group) a household belongs to, in long form.
-- Universe: housing measures use renters and owners with positive income; spending measures use everyone.
CREATE OR REPLACE TABLE flags_long AS
WITH flags AS (
    UNPIVOT (
        SELECT newid, weight, housed, tenure,
               income_quintile, age_group, region, earners_group, household_type,
               burdened::INT AS burdened, severely_burdened::INT AS severely_burdened,
               owner_burdened_upper::INT AS owner_burdened_upper,
               overspend::INT AS overspend, overspend_ex_vehicle::INT AS overspend_ex_vehicle
        FROM measured
    )
    ON burdened, severely_burdened, owner_burdened_upper, overspend, overspend_ex_vehicle
    INTO NAME measure VALUE flag
),
groups AS (
    -- the national total plus each breakdown
    SELECT newid, 'all' AS group_var, 'All households' AS grp FROM measured
    UNION ALL
    SELECT newid, 'renter_or_owner', CASE WHEN tenure = 'Renter' THEN 'Renters' ELSE 'Owners' END
    FROM measured WHERE tenure <> 'Other (no cash rent / student)'
    UNION ALL
    UNPIVOT (SELECT newid, income_quintile, age_group, tenure, region, earners_group, household_type FROM measured)
    ON income_quintile, age_group, tenure, region, earners_group, household_type
    INTO NAME group_var VALUE grp
)
SELECT f.newid, f.weight, f.measure, f.flag, g.group_var, g.grp
FROM flags f
JOIN groups g USING (newid)
WHERE g.grp IS NOT NULL
  AND g.grp <> 'Not stated'                                       -- region suppressed by BLS
  AND NOT (g.group_var = 'tenure' AND g.grp = 'Other (no cash rent / student)')
  AND (f.measure LIKE 'overspend%' OR f.housed);                  -- housing measures: renters + owners only
-- (UNPIVOT drops rows where the flag is NULL, i.e. households outside a measure's universe.)

CREATE OR REPLACE TABLE estimates AS
WITH point AS (
    SELECT measure, group_var, grp,
           SUM(weight * flag) / SUM(weight)          AS share,
           SUM(weight * flag) / 4 / 1e6              AS households_m,
           COUNT(*)                                  AS interviews
    FROM flags_long
    GROUP BY ALL
),
reps AS (
    SELECT fl.measure, fl.group_var, fl.grp, rw.rep,
           SUM(rw.rep_weight * fl.flag) / NULLIF(SUM(rw.rep_weight), 0) AS rep_share
    FROM flags_long fl
    JOIN replicate_weights rw USING (newid)
    GROUP BY ALL
),
se AS (
    SELECT r.measure, r.group_var, r.grp,
           SQRT(AVG(POWER(COALESCE(r.rep_share, p.share) - p.share, 2))) AS se
    FROM reps r
    JOIN point p USING (measure, group_var, grp)
    GROUP BY ALL
)
SELECT p.measure, p.group_var, p.grp AS "group",
       ROUND(100 * p.share, 2)                                   AS pct,
       ROUND(100 * s.se, 2)                                      AS se_pct,
       ROUND(100 * GREATEST(p.share - 1.96 * s.se, 0), 2)        AS ci_low,
       ROUND(100 * (p.share + 1.96 * s.se), 2)                   AS ci_high,
       ROUND(p.households_m, 2)                                  AS households_m,
       p.interviews
FROM point p
JOIN se s USING (measure, group_var, grp)
ORDER BY p.measure, p.group_var, p.grp;
