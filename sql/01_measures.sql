-- Step 1: one row per household interview, with the housing cost burden measures.
-- Input: data/processed/interviews.csv (built by src/build.py from the four BLS files).
-- Each interview covers 3 months of spending; income is annual, so it is divided by 4.

CREATE OR REPLACE TABLE interviews AS
SELECT *
FROM read_csv('data/processed/interviews.csv', header = true, types = {'newid': 'VARCHAR', 'household_id': 'VARCHAR'});

CREATE OR REPLACE TABLE measured AS
WITH base AS (
    SELECT
        *,
        income_before_tax / 4.0 AS income_3m,
        income_after_tax  / 4.0 AS income_after_tax_3m,
        tenure IN ('Renter', 'Owner with mortgage', 'Owner, no mortgage')
            AND income_before_tax > 0 AS housed          -- renters and owners with positive income
    FROM interviews
)
SELECT
    *,
    CASE WHEN housed THEN housing_cost / income_3m END                          AS burden_ratio,
    CASE WHEN housed THEN housing_cost / income_3m > 0.30 END                   AS burdened,
    CASE WHEN housed THEN housing_cost / income_3m > 0.50 END                   AS severely_burdened,
    CASE WHEN housed AND tenure <> 'Renter'
         THEN (housing_cost + owner_repairs_insurance) / income_3m > 0.30 END   AS owner_burdened_upper,
    spend_total > income_after_tax_3m                                           AS overspend,
    spend_total - spend_vehicle_purchase > income_after_tax_3m                  AS overspend_ex_vehicle
FROM base;

-- Replicate weights in long form: one row per interview per replicate (44 per interview).
-- A blank replicate weight was stored as 0 = "not in this half-sample".
CREATE OR REPLACE TABLE replicate_weights AS
UNPIVOT (SELECT newid, COLUMNS('WTREP\d\d') FROM interviews)
ON COLUMNS('WTREP\d\d') INTO NAME rep VALUE rep_weight;

-- Data checks
CREATE OR REPLACE TABLE sql_checks AS
SELECT 'interviews' AS check_name, COUNT(*)::DOUBLE AS value FROM interviews
UNION ALL SELECT 'interviews in housing measures', COUNT(*) FILTER (WHERE housed) FROM measured
UNION ALL SELECT 'replicate weight rows (interviews x 44)', COUNT(*) FROM replicate_weights
UNION ALL SELECT 'U.S. households represented (millions)', ROUND(SUM(weight) / 4 / 1e6, 3) FROM interviews;
